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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    fiscal_position_id = fields.Many2one('account.fiscal.position',
                                         string=u"Position fiscale",
                                         default=lambda self: self.order_id.fiscal_position_id)

    @api.multi
    def fpos_tax_account_mapping(self):
        for rec in self:
            fpos = rec.fiscal_position_id
            tax = rec.product_id.taxes_id.filtered(lambda r: not rec.company_id or r.company_id == rec.company_id)
            new_tax = fpos.map_tax(tax, rec.product_id, rec.order_id.partner_shipping_id) if fpos else tax
            return [(6, 0, new_tax.ids)]

    @api.multi
    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        """ Overwrite of the function defined in sale/models/sale.py l629 to take into account each line's fiscal
        position
        ⚠ Fake compute, but the name was chosen in odoo
        """
        for rec in self:
            rec.tax_id = self.fpos_tax_account_mapping()

    @api.multi
    def write(self, vals):
        if 'fiscal_position_id' in vals:
            vals['tax_id'] = self.fpos_tax_account_mapping()
        return super(SaleOrderLine, self).write(vals)

    @api.multi
    def _prepare_invoice_line(self, qty):
        """ Add this purchase line's fiscal position to the invoice line values """
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        fiscal_position = self.fiscal_position_id
        if not fiscal_position:
            fiscal_position = self.env['account.fiscal.position'].browse(int(
                self.env['ir.config_parameter'].get_param(
                    'account_fiscal_position_line.default_account_fiscal_position_param', 0)))
        res.update({
            'fiscal_position_id': fiscal_position.id,
            'account_id': self.product_id.product_tmpl_id.get_product_accounts(fiscal_position)['income'].id,
        })
        return res
