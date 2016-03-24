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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class TemplateSaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_id = fields.Many2one('res.partner', required=False)
    date_order = fields.Datetime(required=False)
    partner_invoice_id = fields.Many2one('res.partner', required=False)
    partner_shipping_id = fields.Many2one('res.partner', required=False)
    pricelist_id = fields.Many2one('product.pricelist', required=False)
    currency_id = fields.Many2one('res.currency', required=False)
    is_template = fields.Boolean(string="Is a template")
    template_name = fields.Char(string="Template name")
    created_from_template_id = fields.Many2one('sale.order', string="Generated from template", readonly=True)
    created_order_ids = fields.One2many('sale.order', 'created_from_template_id',
                                        string="Sale orders generated from this template", readonly=True)

    @api.constrains('partner_id', 'template_name', 'partner_invoice_id', 'partner_shipping_id', 'pricelist_id',
                    'currency_id', 'date_order')
    def set_sale_order_constraint(self):
        if self.is_template and not self.template_name:
            raise ValidationError(_("This sale order is a template, please fill the name template field."))
        if not self.is_template and not self.partner_id:
            raise ValidationError(_("This sale order is not a template, please fill the customer field."))
        if not self.is_template and not self.partner_invoice_id:
            raise ValidationError(_("This sale order is not a template, please fill the invoice adress field."))
        if not self.is_template and not self.partner_shipping_id:
            raise ValidationError(_("This sale order is not a template, please fill the delivery adress field."))
        if not self.is_template and not self.pricelist_id:
            raise ValidationError(_("This sale order is not a template, please fill the pricelist field."))
        if not self.is_template and not self.currency_id:
            raise ValidationError(_("This sale order is not a template, please fill the currency field."))
        if not self.is_template and not self.date_order:
            raise ValidationError(_("This sale order is not a template, please fill the order date field."))

    @api.multi
    def name_get(self):
        return [(order.id, order.is_template and order.template_name or order.name) for order in self]

    @api.multi
    def create_from_template(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['default_template_id'] = self.id
        ctx['default_partner_ids'] = self.partner_id and [(4, self.partner_id.id, 0)] or False
        return {
            'name': _("Generate sale orders from template %s") % self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.template.generation',
            'target': 'new',
            'context': ctx,
            'domain': []
        }
