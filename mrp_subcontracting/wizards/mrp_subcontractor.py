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

from odoo import models, fields


class MrpSubcontractor(models.TransientModel):
    _name = 'mrp.subcontractor'
    _description = "Mrp Subcontractor"

    def _get_partner_id_domain(self):
        return [('id', 'in',
                self.env['mrp.production'].browse(
                    self.env.context.get('active_id')).product_id.seller_ids.mapped('name').ids)]

    partner_id = fields.Many2one('res.partner', u"Seller", domain=_get_partner_id_domain)

    def subcontract(self):
        # On va créer un PO pour le fournisseur
        mrp = self.env['mrp.production'].browse(self.env.context.get('active_id'))
        purchase_order = self.env['purchase.order'].create({
            'origin': mrp.name,
            'date_order': fields.Datetime.now(),
            'partner_id': self.partner_id.id,
            'date_planned': mrp.date_planned_start,
        })
        purchase_order_line = self.env['purchase.order.line'].create({
            'name': mrp.product_id.name,
            'product_qty': mrp.product_qty,
            'partner_id': self.partner_id.id,
            'date_planned': mrp.date_planned_start,
            'product_uom': mrp.product_id.uom_id.id,
            'product_id': mrp.product_id.id,
            'price_unit': 0,
            'order_id': purchase_order.id,
        })
        # On met à jour les infos via les onchange des models
        purchase_order.onchange_partner_id()
        purchase_order_line.onchange_product_id()
        purchase_order_line.product_qty = purchase_order_line.product_id.seller_ids.filtered(
            lambda r: r.name == purchase_order.partner_id)[:1].get_seller_max_quantity(mrp.product_qty)
        purchase_order_line._onchange_quantity()
        mrp.update({
            'purchase_line_subcontract_id': purchase_order_line,
        })
        view_form_id = self.env.ref('purchase.purchase_order_form').id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_form_id,
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'res_id': purchase_order.id,
            'context': self.env.context,
        }
