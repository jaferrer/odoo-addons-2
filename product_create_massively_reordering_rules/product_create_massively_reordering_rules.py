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


class MassReorderingRulesWizard(models.TransientModel):
    _name = 'mass.reordering.rules.wizard'

    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string=u"Copy Reordering Rule", required=True)
    product_ids = fields.Many2many('product.product', string=u"For Products", required=True)

    @api.multi
    def generate_rules(self):
        self.ensure_one()
        for product in self.product_ids:
            self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product.id)]).unlink()
            self.orderpoint_id.copy({'name': self.orderpoint_id.name,'product_id': product.id})


class MassReorderingRulesProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def launch_ordering_rules_creation(self):
        ctx = self.env.context.copy()
        ctx['default_product_ids'] = [(6, 0, self.ids)]
        return {
            'name': _("Generate Massively Ordering Rules"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mass.reordering.rules.wizard',
            'target': 'new',
            'context': ctx,
        }
