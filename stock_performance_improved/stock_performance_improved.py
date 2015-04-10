# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import time

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, drop_view_if_exists
from openerp import fields, models, api, exceptions, _

class stock_picking_performance_improved(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _assign_moves_to_picking(self):
        """Assign prereserved moves that do not belong to a picking yet to a picking by reconfirming them.
        """
        prereservations = self.env['stock.prereservation'].search([('picking_id','=',False)])
        # todo_move_ids = [p.move_id for p in prereservations]
        todo_moves = prereservations.mapped(lambda p: p.move_id)
        todo_moves.action_confirm()

    @api.multi
    def action_assign(self):
        """Check availability of picking moves.

        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to assign prereserved moves to pickings beforehand.
        :return: True
        """
        self._assign_moves_to_picking()
        return super(stock_picking_performance_improved, self).action_assign()

    #     """ Check availability of picking moves.
    #     This has the effect of changing the state and reserve quants on available moves, and may
    #     also impact the state of the picking as it is computed based on move's states.
    #     Overridden here to improve performance when there are a great number of moves
    #     @return: True
    #     """
    #     for pick in self:
    #         # First confirm the picking if it is not already
    #         if pick.state == 'draft':
    #             self.action_confirm()
    #         # We get all quants in the picking's source location that are not reserved yet
    #         quants = self.env['stock.quant'].search([('location_id','child_of',pick.location_id.id),
    #                                                  ('reservation_id','=',False)])
    #         # We create a dict with the quantities of each product to reserve
    #         product_qties = {}
    #         for quant in quants:
    #             if quant.product_id in product_qties:
    #                 product_qties[quant.product_id] += quant.qty
    #             else:
    #                 product_qties[quant.product_id] = quant.qty
    #         # We iterate on each product and quantities to reserve to get the moves to assign
    #         to_assign_moves = self.env['stock.move']
    #         for product, qty_todo in product_qties.iteritems():
    #             # Filter moves on the product
    #             moves = pick.move_lines.filtered(lambda m: m.product_id == product)
    #             # Get only the needed number of moves to assign the qty to do and add them to to_assign_moves.
    #             qty_left = qty_todo
    #             for move in moves:
    #                 to_assign_moves = to_assign_moves | move
    #                 qty_left -= move.product_qty
    #                 if qty_left <= 0:
    #                     break
    #         if to_assign_moves:
    #             to_assign_moves.action_assign()
    #     return True

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to assign prereserved moves to pickings beforehand
        """
        self._assign_moves_to_picking()
        super(stock_picking_performance_improved, self).rereserve_pick()

    #     for pick in self:
    #         self.rereserve_quants(pick, move_ids = [m.id for m in pick.move_lines if m.availability > 0.0])
    #
    # @api.model
    # @api.returns('stock.picking')
    # def _create_backorder(self, picking, backorder_moves=[]):
    #     """ Move all done lines into a new picking and keep this one as the backorder. This is the opposite of the
    #     standard Odoo behaviour in order to gain speed when there are many moves.
    #     :param picking: A browse record of the picking from which to create a backorder
    #     :param backorder_moves: Unused
    #     :rtype : the id of the picking in which the done lines where put
    #     """
    #     if self.env.context.get('do_only_split', False):
    #         done_moves = self.env['stock.move'].browse(self.env.context.get('split', []))
    #     else:
    #         done_moves = picking.move_lines.filtered(lambda m: m.state in ['done', 'cancel'])
    #     if done_moves:
    #         if done_moves != picking.move_lines:
    #             done_picking = picking.copy({
    #                 'name': '/',
    #                 'move_lines': [],
    #                 'pack_operation_ids': [],
    #                 'backorder_id': picking.backorder_id.id,
    #                 'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    #             })
    #             done_moves.write({'picking_id': done_picking.id})
    #             picking.pack_operation_ids.write({'picking_id': done_picking.id})
    #             picking.write({'backorder_id': done_picking.id})
    #         else:
    #             done_picking = picking
    #         picking.message_post(body=_("New picking <em>%s</em> <b>created</b>.") % (done_picking.name))
    #         return done_picking
    #     return self.env['stock.picking']


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        """Assigns these moves that share the same procurement.group, location_from and location_to to a stock picking.

        Overridden here to assign only if the move is prereserved.
        :param procurement_group: The procurement.group of the moves
        :param location_from: The source location of the moves
        :param location_to: The destination lcoation of the moves
        """
        prereservations = self.env['stock.prereservation'].search([('move_id','in',self.ids)])
        prereserved_moves = prereservations.mapped(lambda p: p.move_id)
        outgoing_moves = self.filtered(lambda m: m.picking_type_id.code == 'outgoing')
        todo_moves = outgoing_moves | prereserved_moves
        if todo_moves:
            return super(stock_move, todo_moves)._picking_assign(procurement_group, location_from, location_to)
        return True

    @api.multi
    def action_assign(self):
        """ Checks the product type and accordingly writes the state.
        Overridden here to also assign a picking if it is not done yet.
        """
        moves_no_pick = self.filtered(lambda m: m.picking_type_id and not m.picking_id)
        moves_no_pick.action_confirm()
        super(stock_move, self).action_assign()


class stock_prereservation(models.Model):
    _name = 'stock.prereservation'
    _description = "Stock Pre-Reservation"
    _auto = False

    id = fields.Integer(readonly=True)
    move_id = fields.Many2one('stock.move', readonly=True, index=True)
    picking_id = fields.Many2one('stock.picking', readonly=True, index=True)

    def init(self, cr):
        drop_view_if_exists(cr, "stock_prereservation")
        cr.execute("""
        create or replace view stock_prereservation as (
            with move_qties as (
                select
                    sm.id as move_id,
                    sm.picking_id,
                    sm.location_id,
                    sm.product_id,
                    sum(sm.product_qty) over (PARTITION BY sm.product_id, COALESCE(sm.picking_id, sm.location_id) ORDER BY priority DESC, date_expected) as qty
                from
                    stock_move sm
                where
                    sm.state = 'confirmed'
                    and sm.picking_type_id is not null
                    and sm.id not in (
                    select reservation_id from stock_quant where reservation_id is not null)
            )
            select
                row_number() over () as id,
                foo.move_id,
                foo.picking_id
            from (
                    select
                        sm.id as move_id,
                        sm.picking_id as picking_id
                    from
                        stock_move sm
                    where
                        sm.id in (
                            select sq.reservation_id from stock_quant sq where sq.reservation_id is not null)
                        and sm.picking_type_id is not null
                union
                    select
                    mq.move_id,
                    mq.picking_id
                from
                    move_qties mq
                    where
                        mq.qty <= (
                            select
                                sum(qty)
                            from
                                stock_quant sq
                            where
                                sq.reservation_id is null
                                and sq.location_id = mq.location_id
                                and sq.product_id = mq.product_id)

            ) foo

        )
        """)


