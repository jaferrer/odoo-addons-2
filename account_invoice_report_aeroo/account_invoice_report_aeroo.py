# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class AccountInvoiceDeleteReport(models.TransientModel):
    _name = 'account.invoice.delete.report'

    @api.model
    def delete_report(self):
        existing_report = self.env.ref('account.account_invoices')
        ir_value = self.env['ir.values']. \
            search([('value', '=', 'ir.actions.report.xml,' + unicode(existing_report.id))])
        ir_value.unlink()


class AccountInvoiceResCompany(models.Model):
    _inherit = 'res.company'

    capital_stock = fields.Float(string=u"Capital stock")


class PaiementMode(models.Model):
    _name = 'paiement.mode'
    _description = "Paiement Mode"

    name = fields.Char(string="Name")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    paiement_mode_id = fields.Many2one('paiement.mode', string=u"Paiement mode")

    @api.multi
    def invoice_print(self):
        super(AccountInvoice, self).invoice_print()
        return self.env['report'].with_context(active_ids=self.ids).get_action(self, 'invoice.report.aeroo')


class ResPartnerReportAeroo(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _display_address(self, address, without_company=False):

        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''

        # get the information that will be injected into the display format
        # get the address format

        address_format = address.country_id.address_format or \
              "%(street)s\n" + (address.street2 and "%(street2)s\n" or "") + "%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        if "%(street2)s\n" in address_format and not address.street2:
            address_format = address_format.replace("%(street2)s\n", "")
        args = {
            'state_code': address.state_id.code or '',
            'state_name': address.state_id.name or '',
            'country_code': address.country_id.code or '',
            'country_name': address.country_id.name or '',
            'company_name': address.parent_name or '',
        }
        for field in self._address_fields():
            if address.street2 or field != 'street2':
                args[field] = getattr(address, field) or ''
        if without_company:
            args['company_name'] = ''
        elif address.parent_id:
            address_format = '%(company_name)s\n' + address_format
        return address_format % args


class ResCompanyReportAeroo(models.Model):
    _inherit = 'res.company'

    invoice_comment = fields.Text(string="Invoice Comment")


class AccountPaymentTermReportAeroo(models.Model):
    _inherit = 'account.payment.term'

    description_for_invoices_1 = fields.Text(string="Description for invoices 1")
    description_for_invoices_2 = fields.Text(string="Description for invoices 2")
