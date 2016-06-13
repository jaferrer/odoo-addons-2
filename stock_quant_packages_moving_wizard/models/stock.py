# -*- coding: utf8 -*-

#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.tools.sql import drop_view_if_exists
from openerp.exceptions import ValidationError
from openerp.tools import float_compare


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def partial_move(self, move_items, product, qty):
        if not move_items.get(product):
            move_items[product] = []
        move_items[product] += [{'quants': self, 'qty': qty}]
        return move_items

    @api.multi
    def move_to(self, dest_location, picking_type_id, move_items=False, is_manual_op=False):
        """
        :param move_items: {product: [{'quants': quants recordset, 'qty': float}, ...], ...}
        """
        move_recordset = self.env['stock.move']
        list_reservation = {}
        if self:
            new_picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
            })
            if move_items:
                for product in move_items.keys():
                    tuples_reservation = []
                    move_tuples = move_items[product]
                    location_from = move_tuples[0]['quants'][0].location_id
                    prec = product.uom_id.rounding
                    new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                        'name': 'Move %s to %s' % (product.name, dest_location.name),
                        'product_id': product.id,
                        'location_id': location_from.id,
                        'location_dest_id': dest_location.id,
                        'product_uom_qty': sum(move_tuple['qty'] for move_tuple in move_tuples),
                        'product_uom': product.uom_id.id,
                        'date_expected': fields.Datetime.now(),
                        'date': fields.Datetime.now(),
                        'picking_type_id': picking_type_id.id,
                        'picking_id': new_picking.id,
                    })
                    for move_tuple in move_tuples:
                        qty_reserved = 0
                        qty_to_reserve = move_tuple['qty']
                        for quant in move_tuple['quants']:
                            # If the new quant does not exceed the requested qty, we move it (end of loop) and continue
                            # If requested qty is reached, we break the loop
                            if float_compare(qty_reserved, qty_to_reserve, precision_rounding=prec) >= 0:
                                break
                            # If the new quant exceeds the requested qty, we split it and reserve the good qty
                            elif float_compare(qty_reserved + quant.qty, qty_to_reserve, precision_rounding=prec) > 0:
                                self.env['stock.quant']._quant_split(quant, qty_reserved + quant.qty - qty_to_reserve)
                            tuples_reservation += [(quant, quant.qty)]
                    list_reservation[new_move] = tuples_reservation
                    move_recordset = move_recordset | new_move
            else:
                values = self.env['stock.quant'].read_group([('id', 'in', self.ids)],
                                                            ['product_id', 'location_id', 'qty'],
                                                            ['product_id', 'location_id'], lazy=False)
                for val in values:
                    new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                        'name': 'Move %s to %s' % (val['product_id'][1], dest_location.name),
                        'product_id': val['product_id'][0],
                        'location_id': val['location_id'][0],
                        'location_dest_id': dest_location.id,
                        'product_uom_qty': val['qty'],
                        'product_uom':
                            self.env['product.product'].search([('id', '=', val['product_id'][0])]).uom_id.id,
                        'date_expected': fields.Datetime.now(),
                        'date': fields.Datetime.now(),
                        'picking_type_id': picking_type_id.id,
                        'picking_id': new_picking.id,
                    })
                    quants = self.env['stock.quant'].search(
                        [('id', 'in', self.ids), ('product_id', '=', val['product_id'][0])])
                    qtys = quants.read(['id', 'qty'])
                    list_reservation[new_move] = []
                    for qt in qtys:
                        list_reservation[new_move].append((self.env['stock.quant'].search(
                            [('id', '=', qt['id'])]), qt['qty']))

                    move_recordset = move_recordset | new_move

            if move_recordset:
                move_recordset.action_confirm()
            for new_move in list_reservation.keys():
                assert new_move.picking_id == new_picking, \
                    _("The moves of all the quants could not be assigned to the same picking.")
                self.quants_reserve(list_reservation[new_move], new_move)
            new_picking.do_prepare_partial()
            packops = new_picking.pack_operation_ids
            packops.write({'location_dest_id': dest_location.id})
            if not is_manual_op:
                new_picking.do_transfer()
        return move_recordset


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    picking_type_id = fields.Many2one(
        "stock.picking.type", string=u"Mouvement de déplacement par défault")


class Stock(models.Model):
    _name = 'stock.product.line'
    _auto = False
    _order = 'package_id asc, product_id asc'

    product_id = fields.Many2one('product.product', readonly=True, index=True, string='Article')
    package_id = fields.Many2one("stock.quant.package", u"Colis", index=True)
    lot_id = fields.Many2one("stock.production.lot", string=u"Numéro de série")
    qty = fields.Float(u"Quantité")
    uom_id = fields.Many2one("product.uom", string=u"Unité de mesure d'article")
    location_id = fields.Many2one("stock.location", string=u"Emplacement")

    def init(self, cr):
        drop_view_if_exists(cr, 'stock_product_line')
        cr.execute("""SELECT COALESCE(rqx.product_id,0)
||'-'||COALESCE(rqx.package_id,0)||'-'||COALESCE(rqx.lot_id,0)||'-'||
COALESCE(rqx.uom_id,0)||'-'||COALESCE(rqx.location_id,0) AS id,
rqx.*
FROM
(SELECT
            sq.product_id,
            sq.package_id,
            sq.lot_id,
            sum(sq.qty) qty,
            pt.uom_id,
            sq.location_id
FROM
stock_quant sq
LEFT JOIN product_product pp ON pp.id=sq.product_id
LEFT JOIN product_template pt ON pp.product_tmpl_id=pt.id
GROUP BY
sq.product_id,
sq.package_id,
sq.lot_id,
pt.uom_id,
sq.location_id
UNION ALL
SELECT
            NULL product_id,
            sqp.id package_id,
            NULL lot_id,
            0 qty,
            NULL uom_id,
            sqp.location_id
FROM
stock_quant_package sqp
WHERE exists (SELECT 1
FROM
stock_quant sq
LEFT JOIN stock_quant_package sqp_bis ON sqp_bis.id=sq.package_id
WHERE sqp_bis.id=sqp.id
GROUP BY sqp_bis.id
HAVING count(DISTINCT sq.product_id)<>1)
) rqx
        """)

    @api.multi
    def move_products(self):
        if self:
            location = self[0].location_id
            if any([line.location_id != location for line in self]):
                raise ValidationError(_("Impossible to move simultaneously products of different locations"))
        ctx = self.env.context.copy()
        ctx['active_ids'] = self.ids
        return {
            'name': _("Move products"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.move.wizard',
            'target': 'new',
            'context': ctx,
        }
