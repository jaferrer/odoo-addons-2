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

from openerp import fields, models, api, exceptions, _
from openerp.tools import float_compare


class QuantitiesModificationsSaleOrder(models.Model):
    _inherit = 'sale.order'

    order_line = fields.One2many('sale.order.line', 'order_id', readonly=False, states={'done': [('readonly', True)],
                                                                                        'cancel': [('readonly', True)]})


class QuantitiesModificationsProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def compute_delivrered_ordered_quantities(self, line_uom_id):
        delivered_qty = 0
        ordered_qty = 0
        done_uom = []
        for procurement in self:
            if procurement.product_uom not in done_uom:
                procurements_done_current_uom = self. \
                    filtered(lambda proc: proc.product_uom == procurement.product_uom and proc.state == 'done')
                procurements_not_cancel_current_uom = self. \
                    filtered(lambda proc: proc.product_uom == procurement.product_uom and proc.state != 'cancel')
                delivered_qty += self.env['product.uom']. \
                    _compute_qty(procurement.product_uom.id,
                                 sum([proc.product_qty for proc in procurements_done_current_uom]),
                                 to_uom_id=line_uom_id, round=True, rounding_method='UP')
                ordered_qty += self.env['product.uom']. \
                    _compute_qty(procurement.product_uom.id,
                                 sum([proc.product_qty for proc in procurements_not_cancel_current_uom]),
                                 to_uom_id=line_uom_id,
                                 round=True, rounding_method='UP')
                done_uom += [procurement.product_uom]
        return delivered_qty, ordered_qty


class QuantitiesModificationsSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_uom_qty = fields.Float(readonly=False, states={'done': [('readonly', True)],
                                                           'cancel': [('readonly', True)]})
    price_unit = fields.Float(readonly=False, states={'done': [('readonly', True)],
                                                      'cancel': [('readonly', True)]})

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
    def update_procurements_for_new_qty_or_uom(self, vals, line_uom_id):
        self.ensure_one()
        procs_to_unlink = False
        delivered_qty, ordered_qty = self.procurement_ids.compute_delivrered_ordered_quantities(line_uom_id)
        if vals.get('product_uom') or vals.get('product_uom_qty') and \
                        float_compare(vals['product_uom_qty'], 0,
                                      precision_rounding=self.product_id.uom_id.rounding) != 0:
            if self.procurement_ids:
                if float_compare(vals['product_uom_qty'],
                                 ordered_qty, precision_rounding=self.product_id.uom_id.rounding) > 0:
                    # If the qty of the line is increased, we increase the qty of the first procurement.
                    new_proc = self.procurement_ids[0]. \
                        copy({'product_qty': vals['product_uom_qty'] - ordered_qty,
                              'product_uom': line_uom_id})
                    new_proc.run()
                elif float_compare(vals['product_uom_qty'], ordered_qty,
                                   precision_rounding=self.product_id.uom_id.rounding) < 0:
                    if float_compare(vals['product_uom_qty'], delivered_qty,
                                     precision_rounding=self.product_id.uom_id.rounding) < 0:
                        raise exceptions.except_orm(_("Error!"), _("Impossible to set the line quantity lower "
                                                                   "than the delivered quantity."))
                    else:
                        # Let's remove undelivered procurements
                        procs_to_unlink = self.procurement_ids. \
                            filtered(lambda proc: proc.state not in ['cancel', 'done'])
                        if float_compare(vals['product_uom_qty'], delivered_qty,
                                         precision_rounding=self.product_id.uom_id.rounding) > 0:
                            # Creation of the missing procurement.
                            new_proc = self.procurement_ids[0]. \
                                copy({'product_qty': vals['product_uom_qty'] - delivered_qty,
                                      'product_uom': line_uom_id})
                            new_proc.run()
        if procs_to_unlink:
            procs_to_unlink.cancel()
            procs_to_unlink.unlink()
        elif 'product_uom_qty' in vals.keys() and \
                        float_compare(vals['product_uom_qty'], 0,
                                      precision_rounding=self.product_id.uom_id.rounding) == 0:
            # If the quantity of a line is set to zero, we delete the linked procurements and the line itself.
            if self.procurement_ids.filtered(lambda proc: proc.state == 'done'):
                raise exceptions.except_orm(_("Error!"), _("Impossible to cancel a procurement in state done."))
            elif self.procurement_ids:
                self.procurement_ids.cancel()
                self.procurement_ids.unlink()
            self.unlink()

    @api.multi
    def write(self, vals):
        result = super(QuantitiesModificationsSaleOrderLine, self).write(vals)
        # Overwriting the 'write' function, in order to deal with a modification of the quantity of a sale order line.
        for rec in self:
            line_uom_id = vals.get('product_uom', rec.product_uom.id)
            if rec.order_id.state not in ['draft', 'cancel', 'done']:
                if vals.get('price_unit'):
                    active_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                                  ('procurement_id', 'in', rec.procurement_ids.ids),
                                                                  ('state', 'not in', ['draft', 'cancel', 'done'])])
                    active_moves.write({'price_unit': vals['price_unit']})
                rec.update_procurements_for_new_qty_or_uom(vals, line_uom_id)
        return result
