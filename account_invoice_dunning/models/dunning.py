# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _, osv


class AccountInvoiceRelanceConfig(models.Model):
    _name = 'account.invoice.dunning.type'

    def _get_domain_mail_template(self):
        return [('model_id', '=', self.env.ref('account_invoice_dunning.model_account_invoice_dunning').id)]

    name = fields.Char(required=True, string=u"Name")
    number = fields.Integer(u"Dunning number", default=1, required=True)
    sequence_id = fields.Many2one('ir.sequence', string=u"Sequence")
    report_id = fields.Many2one('ir.actions.report.xml', string=u"Report",
                                domain=[('model', '=', 'account.invoice.dunning')], required=True)
    mail_template_id = fields.Many2one('mail.template', string=u"Mail Template", domain=_get_domain_mail_template,
                                       required=True)
    company_id = fields.Many2one('res.company', string=u"Company", default=lambda self: self.env.user.company_id)
    delay = fields.Integer(u"Delay before next dunning", help=u"Number of days before next dunning")

    @api.multi
    def _get_dunning_name(self):
        return self.ensure_one().sequence_id and self.sequence_id._next() or ""

    _sql_constraints = [
        ('dunning_number_unique', 'unique (number, company_id)', u"The Dunning number must be unique per company !"),
    ]


class AccountInvoiceRelance(models.Model):
    _name = 'account.invoice.dunning'
    _inherit = ['mail.thread']
    _description = u"Invoice Dunning"
    _order = 'id DESC'

    name = fields.Char(u"Name")
    date_done = fields.Date(u"Dunning date done", readonly=True)
    state = fields.Selection([
        ('draft', u"Draft"),
        ('send', u"Sent"),
        ('cancel', u"Cancel"),
        ('done', u"Done")], string=u"State", readonly=True, default='draft', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string=u"Partner")
    company_id = fields.Many2one('res.company', string=u"Company", default=lambda self: self.env.user.company_id)
    dunning_type_id = fields.Many2one('account.invoice.dunning.type', string=u"Dunning Type")
    report_id = fields.Many2one('ir.actions.report.xml', string=u"Report", related='dunning_type_id.report_id',
                                readonly=True)
    sequence_id = fields.Many2one('ir.sequence', related='dunning_type_id.sequence_id', readonly=True)
    mail_template_id = fields.Many2one('mail.template', string=u"Mail Template",
                                       related='dunning_type_id.mail_template_id', readonly=True)
    invoice_ids = fields.Many2many('account.invoice', string=u"Invoices")
    amount_total_signed = fields.Float(u"Total", compute='_compute_amounts')
    residual_signed = fields.Float(u"Residual", compute='_compute_amounts')
    note = fields.Text(u"Notes")
    user_id = fields.Many2one('res.users', u"Responsible")

    @api.multi
    def _compute_amounts(self):
        for rec in self:
            amount = 0
            residual = 0
            for invoice in rec.invoice_ids:
                amount += invoice.amount_total_signed
                residual += invoice.residual_signed
            rec.amount_total_signed = amount
            rec.residual_signed = residual

    @api.model
    def _get_existing_dunning(self, invoice_id, dunning_config_id):
        return self.search(self._get_existing_dunning_domain(invoice_id, dunning_config_id))

    @api.multi
    def action_done(self):
        # Met à jour la date de prochaine Relance à la validation de la Relance
        if self.dunning_type_id.delay:
            date_next = fields.Date.to_string(datetime.date.today() + relativedelta(days=self.dunning_type_id.delay))
            self.invoice_ids.write({'date_next_dunning': date_next})
        self.write({'state': 'done'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def _get_existing_dunning_domain(self, invoice_id, dunning_type_id):
        return [('partner_id', '=', invoice_id.partner_id.id),
                ('dunning_type_id', '=', dunning_type_id.id),
                ('company_id', '=', invoice_id.company_id.id),
                ('state', '=', 'draft')
                ]

    @api.multi
    def action_print_dunning(self):
        self.ensure_one()
        res = self.env['report'].with_context(active_ids=self.ids).get_action(self, self.report_id.report_name)
        vals = {'state': 'send'}
        if not self.date_done:
            vals['date_done'] = fields.Date.today()
        self.write(vals)
        return res

    @api.multi
    def action_send_mail(self):
        self.ensure_one()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model=self._name,
            default_res_id=self.id,
            default_composition_mode='comment',
            default_template_id=self.mail_template_id.ensure_one().id,
        )
        ctx.update(self._default_dict_send_mail_action())
        return {
            'name': _(u"Send a message"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _default_dict_send_mail_action(self):
        return {'final_dunning_state': 'send'}

    @api.multi
    def _get_action_view(self):
        if len(self.ids) > 1:
            ctx = dict(self.env.context,
                       search_default_group_partner_id=True,
                       search_default_group_dunning_type_id=True)
            res = {
                'name': _(u"Dunning"),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice.dunning',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'domain': [('id', 'in', self.ids)]
            }

        else:
            res = {
                'name': self.name,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref("account_invoice_dunning.invoice_dunning_form_view").id,
                'res_model': 'account.invoice.dunning',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
            }

        return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    invoice_dunning_ids = fields.Many2many('account.invoice.dunning', string=u"Dunnings")
    dunning_number = fields.Integer(u"Number of Dunning send", compute='_compute_dunning_number')
    date_next_dunning = fields.Date(u"Date next dunning")

    @api.multi
    @api.depends('invoice_dunning_ids')
    def _compute_dunning_number(self):
        for rec in self:
            rec.dunning_number = len(rec.invoice_dunning_ids.filtered(lambda it: it.state in ['send', 'done']))

    @api.model
    def create(self, vals):
        """
        Si aucune date de prochaine relance n'est renseignée dans la facture, on la crée à partir de la date de validité
        standard des Relances de la société.
        """
        if not vals.get('date_next_dunning'):
            days = self.env.user.company_id.sending_validity_duration
            vals['date_next_dunning'] = fields.Date.to_string(datetime.datetime.now() + datetime.timedelta(days=days))
        return super(AccountInvoice, self).create(vals)

    @api.multi
    def action_create_dunning(self):
        return self._create_dunning()._get_action_view()

    @api.multi
    def _no_next_dunning(self):
        raise osv.osv.except_orm(_(u"Error !"), _(u"No next Dunning Type for the invoice %s" % self.number))

    @api.multi
    def _validate_to_create_dunning(self):
        if self.state != 'open':
            raise osv.osv.except_orm(_(u"Error !"), _(u"You can't create a Dunning on an invoice which is not open"))
        if self.type != 'out_invoice':
            raise osv.osv.except_orm(_(u"Error !"), _(u"You can only create a Dunning on an Sale Invoice"))

    @api.multi
    def _get_next_dunning_type(self):
        dunning_type_ids = self.invoice_dunning_ids.filtered(lambda it: it.state == 'send').mapped('dunning_type_id')
        return self.env['account.invoice.dunning.type'].search(
            [('id', 'not in', dunning_type_ids.ids),
             '|', ('company_id', '=', self.company_id.id),
             ('company_id', '=', False)],
            order='number asc', limit=1)

    @api.multi
    def _prepare_invoice_dunning(self, dunning_type):
        self.ensure_one()
        return {
            'dunning_type_id': dunning_type.id,
            'invoice_ids': [(4, self.id, {})],
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'name': dunning_type._get_dunning_name()
        }

    @api.multi
    def action_invoice_paid(self):
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        for rec in to_pay_invoices:
            for dunning in rec.invoice_dunning_ids:
                if dunning.state == 'draft':
                    rec.invoice_dunning_ids = [(3, dunning.id)]
        return super(AccountInvoice, self).action_invoice_paid()

    @api.multi
    def _create_dunning(self):
        result = self.env['account.invoice.dunning']
        for rec in self:
            rec._validate_to_create_dunning()
            next_dunning_type = rec._get_next_dunning_type()
            if next_dunning_type:
                existing_dunning = self.env['account.invoice.dunning']._get_existing_dunning(rec, next_dunning_type)
                if existing_dunning:
                    existing_dunning.invoice_ids = [(4, rec.id, {})]
                else:
                    existing_dunning = self.env['account.invoice.dunning'].create(
                        rec._prepare_invoice_dunning(next_dunning_type))
                result |= existing_dunning
            else:
                rec._no_next_dunning()
        return result

    @api.model
    def compute_dunning_invoice(self):
        """
        Cron pour créer des Relances sur les Factures dont la date de prochaine relance a été dépassée et qui n'ont
        pas de Relance en cours.
        """
        need_dunning_invoices = self.env['account.invoice'].search([
            ('state', '=', 'open'),
            ('date_next_dunning', '!=', False),
            ('date_next_dunning', '<=', fields.Date.today())
        ])
        invoices_dunning_to_create = self.env['account.invoice']
        for invoice in need_dunning_invoices:
            if not invoice.invoice_dunning_ids.filtered(lambda x: x.state not in ('cancel', 'done')):
                invoices_dunning_to_create |= invoice

        invoices_dunning_to_create._create_dunning()


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self.env.context or {}
        if context.get('default_model') == 'account.invoice.dunning' \
                and context.get('default_res_id', -1) > 0 \
                and context.get('final_dunning_state'):
            dunning = self.env['account.invoice.dunning'].browse(context['default_res_id'])
            vals = {'state': context.get('final_dunning_state')}
            if not dunning.date_done:
                vals['date_done'] = fields.Date.today()
            dunning.write(vals)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
