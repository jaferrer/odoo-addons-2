# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class QuantitiesModificationsSaleOrder(models.Model):
    _inherit = 'sale.order'

    order_line = fields.One2many('sale.order.line', 'order_id', readonly=False, states={'done': [('readonly', True)],
                                                                                        'cancel': [('readonly', True)]})

class QuantitiesModificationsSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_uom_qty = fields.Float(readonly=False, states={'done': [('readonly', True)],
                                                           'cancel': [('readonly', True)]})
    price_unit = fields.Float(readonly=False)

    @api.multi
    def unlink(self):
        # Deletion of the corresponding procurements when deleting a sale order line.
        for rec in self:
            if rec.procurement_ids:
                rec.procurement_ids.cancel()
                rec.procurement_ids.unlink()
        self.button_cancel()
        return super(QuantitiesModificationsSaleOrderLine, self).unlink()

    @api.model
    def create(self, vals):
        # Creation of corresponding procurements when adding a sale order line.
        result = super(QuantitiesModificationsSaleOrderLine, self).create(vals)
        if result.order_id and result.order_id.state not in ['draft', 'done', 'cancel']:
            result.state = 'confirmed'
            # Lets's call 'action_ship_create' function using old api, in order to allow the system to change the
            # context (which is a frozendict in new api).
            context = self.env.context.copy()
            # Creation of the corresponding procurement orders
            self.pool.get('sale.order').action_ship_create(self.env.cr, self.env.uid, [result.order_id.id], context)
        return result

    @api.multi
    def write(self, vals):
        result = super(QuantitiesModificationsSaleOrderLine, self).write(vals)
        # Overwriting the 'write' function, in order to deal with a modification of the quantity of a sale order line.
        for rec in self:
            if rec.order_id.state not in ['draft', 'cancel', 'done']:
                if vals.get('price_unit'):
                    active_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                                  ('procurement_id', 'in', rec.procurement_ids.ids),
                                                                  ('state', 'not in', ['draft', 'cancel', 'done'])])
                    active_moves.write({'price_unit': vals['price_unit']})
                if vals.get('product_uom_qty') and vals['product_uom_qty'] != 0:
                    if rec.procurement_ids:
                        sum_procurements = sum([x.product_qty for x in rec.procurement_ids if
                                                x.state not in ['cancel', 'done']])
                        if vals['product_uom_qty'] > sum_procurements:
                            # If the qty of the line is increased, we increase the qty of the first procurement.
                            sum_ordered_qty = sum([proc.product_qty for proc in rec.procurement_ids])
                            new_proc = rec.procurement_ids[0].copy({'product_qty': vals['product_uom_qty'] - sum_ordered_qty})
                            new_proc.run()
                        elif vals['product_uom_qty'] < sum_procurements:
                            # If the qty of the line is decreased, we delete all the procurements linked to the line.
                            # Other ones will be generated later.
                            rec.procurement_ids.cancel()
                            rec.procurement_ids.unlink()
                    if not rec.procurement_ids:
                        # Creation of the procurements for lines which have no ones.
                        self.pool.get('sale.order').action_ship_create(self.env.cr, self.env.uid, [rec.order_id.id],
                                                                       self.env.context.copy())
                if vals.get('product_uom_qty') == 0:
                    # If the quantity of a line is set to zero, we delete the linked procurements and the line itself.
                    if rec.procurement_ids:
                        rec.procurement_ids.cancel()
                        rec.procurement_ids.unlink()
                    rec.unlink()
        return result
