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
from datetime import datetime

from openerp import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.multi
    def move_to(self, dest_location, picking_type_id, move_items=False, is_manual_op=False):
        move_recordset = self.env['stock.move']
        list_reservation = {}
        if self:
            new_picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
            })

            if move_items:
                for item in self:
                    new_move = self.env['stock.move'].with_context(mail_notrack=True).create({
                        'name': 'Move %s to %s' % (item.product_id.name, dest_location.name),
                        'product_id': item.product_id.id,
                        'location_id': item.location_id.id,
                        'location_dest_id': dest_location.id,
                        'product_uom_qty': item.qty if not move_items else move_items[item.id].qty,
                        'product_uom': item.product_id.uom_id.id,
                        'date_expected': fields.Datetime.now(),
                        'date': fields.Datetime.now(),
                        'picking_type_id': picking_type_id.id,
                        'picking_id': new_picking.id,
                    })
                    list_reservation[new_move] = [(item, new_move.product_uom_qty)]
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

