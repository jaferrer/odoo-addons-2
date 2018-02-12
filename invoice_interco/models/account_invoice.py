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

from openerp import models, api


class IntercoAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    # inverse_invoice_id = fields.Many2one('account.invoice', u"Invoice Origin")

    @api.multi
    def invoice_validate(self):
        res = super(IntercoAccountInvoice, self).invoice_validate()
        self.make_reverse_invoice()
        return res

    @api.multi
    def make_reverse_invoice(self):
        res = self.env['account.invoice']
        for rec in self:
            if rec._is_allowed_company_auto_reverse_invoice():
                res |= rec.sudo().copy(rec._prepare_reverse_invoice())
        res = self._manage_reverse_invoice(res)
        return res

    @api.multi
    def _is_allowed_company_auto_reverse_invoice(self):
        self.ensure_one()
        comp = self.env['res.company'].search([]).mapped('partner_id')
        return self.user_id.has_group('base.group_multi_company') and self.partner_id in comp

    @api.multi
    def _prepare_reverse_invoice(self):
        self.ensure_one()
        return {
            'partner_id': self.company_id.partner_id.id,
            'company_id': self.env['res.company'].search([('partner_id', '=', self.partner_id.id)]).id,
            'type': self._inverse_type()[self.type],
            'origin': self.number,
        }

    @api.multi
    def _manage_reverse_invoice(self, reverse):
        return reverse

    @api.multi
    def _inverse_type(self):
        return {
            'in_invoice': 'out_invoice',
            'out_invoice': 'in_invoice',
            'in_refund': 'out_refund',
            'out_refund': 'in_refund',
        }
