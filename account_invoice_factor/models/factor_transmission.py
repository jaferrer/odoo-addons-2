# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this
#

import logging
import base64
from datetime import datetime, date
from openerp import fields, models, api, _, exceptions

_logger = logging.getLogger(__name__)


class FactorTransmission(models.Model):
    _name = 'factor.transmission'
    _inherit = ['mail.thread']

    bank_id = fields.Many2one('res.partner.bank', string=u"Factor bank",
                              domain="[('factor_cga_account_number', '!=', False)]", required=True)

    bank_factor_settings_errors = fields.Text(u"settings errors", readonly=True, compute="_onchange_bank_id")
    invoice_ids = fields.Many2many('account.invoice', string=u"invoices", compute="_onchange_bank_id", store=True)
    debtors_file_id = fields.Many2one('ir.attachment', string=u"debtors file", readonly=True)
    open_items_file_id = fields.Many2one('ir.attachment', string=u"open items files", readonly=True)
    is_transmit_to_factor = fields.Boolean(u"Transmitted to factor", readonly=True, compute="_compute_fields")

    @api.multi
    def _create_attachment(self, binary, name, folder=False):
        self.ensure_one()
        if not binary:
            return False
        return self.env['ir.attachment'].create({
            'type': 'binary',
            'res_model': self._name,
            'res_name': name,
            'datas_fname': name,
            'name': name,
            'datas': binary,
            'res_id': self.id,
            'parent_id': folder and folder.id or False,
        })

    @api.multi
    def _compute_fields(self):
        for rec in self:
            rec.is_transmit_to_factor = rec.message_last_post is True

    @api.multi
    def _get_invoices(self):
        self.ensure_one()
        domain = [
            ('partner_id.commercial_partner_id.factor_bank_id', '=', self.bank_id.id),
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('allow_transmit_factor', '=', True),
            ('state', '!=', 'draft'),
            ('factor_needs_transmission', '=', True)
        ]
        return self.env['account.invoice'].search(domain)

    @api.multi
    @api.onchange('bank_id')
    def _onchange_bank_id(self):
        for rec in self:
            # raz computed fields
            rec.bank_factor_settings_errors = False
            # init factor config errors
            if not rec.bank_id:
                return

            errors = rec.bank_id.get_factor_settings_errors()
            if errors:
                rec.bank_factor_settings_errors = "\n".join(errors)
                return

            rec.invoice_ids = self._get_invoices()

    # region HANDLING DEBTOR & OPEN ITEMS IR.ATTACHMENT

    @api.multi
    def _generate_attachments(self):
        self.ensure_one()

        # clean up attachments
        self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', 'in', self.ids)]).unlink()

        if not self.invoice_ids:
            return False

        open_items_contents = []
        debtors_contents = []
        for invoice in self.invoice_ids:
            open_items_contents.append(self._get_open_items_line(invoice))
            debtors_contents.append(self._get_debtor_line(invoice))

        open_items_filename = 'NC%s0_%s.csv' % (self.bank_id.factor_cga_account_number,
                                                datetime.today().strftime("%Y%m%d_%H%M%S"))
        debtor_filename = 'NA%s0_%s.csv' % (self.bank_id.factor_cga_account_number,
                                            datetime.today().strftime("%Y%m%d_%H%M%S"))

        folder = self.env.ref('account_invoice_factor.dir_factor')
        open_items_contents = base64.encodestring("\n".join(open_items_contents).encode('utf-8'))
        debtors_contents = base64.encodestring("\n".join(debtors_contents).encode('utf-8'))
        self.open_items_file_id = self._create_attachment(open_items_contents, open_items_filename, folder)
        self.debtors_file_id = self._create_attachment(debtors_contents, debtor_filename, folder)

    @api.multi
    def _get_debtor_line(self, invoice):
        self.ensure_one()
        partner = self.bank_id.partner_id.commercial_partner_id

        if not partner.siren and partner.country_id.code == 'FR':
            raise exceptions.except_orm(u"Factor error for invoice %s: Siren is a mandatory field for french debtors"
                                        % invoice.number)

        line_mask = u'ADEB;.;04;AAAAMMJJ;A;{file_creation_date};{company_code};{account_number};{cga_account_number};' \
                    u'{cga_contract_number};{contract_type};{cga_currency_code};{siren};{nic_number};;;' \
                    u'{company_name};{address_line1};{address_line2};;{postal_code};{town};{country_code};{phone};' \
                    u'{partner_number};;;;;;;;;{vat_number};{country_code};;;;;;;;;;;;;{partner_number}'

        return line_mask.format(
            file_creation_date=date.today().strftime("Y%m%d"),
            company_code=self.bank_id.factor_company_code,
            account_number=self.bank_id.factor_account_number,
            cga_account_number=self.bank_id.factor_cga_account_number,
            cga_contract_number=self.bank_id.factor_contract_number,
            contract_type=self.bank_id.factor_contract_type,
            cga_currency_code=self.bank_id.factor_currency_id.name,
            siren=partner.siren or "",
            nic_number=partner.siret[len(partner.siret) - 5:] if partner.siret else "",
            company_name=partner.name,
            address_line1=partner.street or "",
            address_line2=partner.street2 or "",
            postal_code=partner.zip,
            town=partner.city,
            country_code=partner.country_id.code,
            phone=partner.phone,
            partner_number=partner.number,
            vat_number=invoice.num_vat_id and invoice.num_vat_id.vat or "",
        )

    @api.multi
    def _get_open_items_line(self, invoice):
        self.ensure_one()
        if invoice.type not in ['out_invoice', 'out_refund']:  # facture client ou avoir client
            raise exceptions.except_orm(u"Factor error for invoice %s: Unknown invoice type '%s' for factor transaction"
                                        % (self.number, self.type))

        is_invoice = invoice.type == 'out_invoice'

        def format_amount(amount):
            return '%+.2f' % amount if is_invoice else 0 - amount

        line_mask = u'CDFM;.;04;AAAAMMJJ;A;{file_creation_date};{company_code};{account_number};{cga_account_number};' \
                    u'{cga_contract_number};{contract_type};{cga_currency_code};{debtor_account_number};' \
                    u'{closing_date};{currency_code};{operation_type};{document_number};{document_date};' \
                    u'{registration_date};{vat_included_amount};;{balance};{due_date1};{amount1}'

        return line_mask.format(
            file_creation_date=date.today().strftime("Y%m%d"),  # file creation date
            company_code=self.bank_id.factor_company_code,
            account_number=self.bank_id.factor_account_number,
            cga_account_number=self.bank_id.factor_cga_account_number,
            cga_contract_number=self.bank_id.factor_contract_number,
            contract_type=self.bank_id.factor_contract_type,
            cga_currency_code=self.bank_id.factor_currency_id.name,
            debtor_account_number=invoice.partner_id.commercial_partner_id.number,
            closing_date=invoice.date_invoice.replace('-', ''),
            currency_code=invoice.currency_id.name,
            operation_type='01' if is_invoice else '25',  # invoice or invoice cancellation
            document_number=invoice.number,
            document_date=invoice.date_invoice.replace('-', ''),
            registration_date=invoice.create_date[:10].replace('-', ''),
            vat_included_amount=format_amount(invoice.amount_total),
            balance=format_amount(invoice.residual),
            due_date1=invoice.date_due.replace('-', ''),
            amount1=format_amount(invoice.reste_a_payer)
        )
    # endregion

    @api.multi
    def action_display_mail_wizard(self):
        """ Open a window to compose an email"""
        template = self.env.ref('account_invoice_factor.mail_template_transmit_factor', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='factor.transmission',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            invoice_ids_to_factor=self.invoice_ids.ids,
            re_mail=self.message_last_post is True
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.model
    def create(self, vals):
        rec = super(FactorTransmission, self).create(vals)
        if rec:
            rec.invoice_ids = rec._get_invoices()
            rec._generate_attachments()
        return rec
