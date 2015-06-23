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
    def assign_moves_to_picking(self):
        """Assign prereserved moves that do not belong to a picking yet to a picking by reconfirming them.
        """
        prereservations = self.env['stock.prereservation'].search([('picking_id','=',False)])
        todo_moves = prereservations.mapped(lambda p: p.move_id)
        to_assign_moves = todo_moves.filtered(lambda m: m.state == 'assigned')
        todo_moves.action_confirm()
        # We reassign moves that were assigned beforehand because action_confirmed changed the state
        to_assign_moves.action_assign()

    @api.multi
    def action_assign(self):
        """Check availability of picking moves.

        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        Overridden here to assign prereserved moves to pickings beforehand.
        :return: True
        """
        self.assign_moves_to_picking()
        return super(stock_picking_performance_improved, self).action_assign()

    @api.multi
    def rereserve_pick(self):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        Overridden here to assign prereserved moves to pickings beforehand
        """
        self.assign_moves_to_picking()
        super(stock_picking_performance_improved, self).rereserve_pick()


class stock_move(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        """Assigns these moves that share the same procurement.group, location_from and location_to to a stock picking.

        Overridden here to assign only if the move is prereserved.
        :<param procurement_group: The procurement.group of the moves
        :param location_from: The source location of the moves
        :param location_to: The destination lcoation of the moves
        """
        prereservations = self.env['stock.prereservation'].search([('move_id','in',self.ids)])
        prereserved_moves = prereservations.mapped(lambda p: p.move_id)
        outgoing_moves = self.filtered(lambda m: m.picking_type_id.code == 'outgoing')
        incoming_moves = self.filtered(lambda m: m.picking_type_id.code == 'incoming')
        todo_moves = outgoing_moves | prereserved_moves | incoming_moves
        # Only assign prereserved or outgoing moves to pickings
        if todo_moves:
            # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
            # In the next version, the locations on the picking should be stored again.
            query = """
                SELECT stock_picking.id FROM stock_picking, stock_move
                WHERE
                    stock_picking.state in ('draft','waiting','confirmed','partially_available','assigned') AND
                    stock_move.picking_id = stock_picking.id AND
                    stock_move.location_id = %s AND
                    stock_move.location_dest_id = %s AND
            """
            params = (location_from, location_to)
            if not procurement_group:
                query += "stock_picking.group_id IS NULL LIMIT 1"
            else:
                query += "stock_picking.group_id = %s LIMIT 1"
                params += (procurement_group,)
            self.env.cr.execute(query, params)
            [pick_id] = self.env.cr.fetchone() or [None]
            if not pick_id:
                move = self[0]
                values = {
                    'origin': move.origin,
                    'company_id': move.company_id and move.company_id.id or False,
                    'move_type': move.group_id and move.group_id.move_type or 'direct',
                    'partner_id': move.partner_id.id or False,
                    'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
                }
                pick = self.env['stock.picking'].create(values)
                pick_id = pick.id
            return self.write({'picking_id': pick_id})
        else:
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

    move_id = fields.Many2one('stock.move', readonly=True, index=True)
    picking_id = fields.Many2one('stock.picking', readonly=True, index=True)

    def init(self, cr):
        drop_view_if_exists(cr, "stock_prereservation")
        cr.execute("""
        create or replace view stock_prereservation as (
            with recursive top_parent(loc_id, top_parent_id) as (
                    select
                        sl.id as loc_id, sl.id as top_parent_id
                    from
                        stock_location sl
                        left join stock_location slp on sl.location_id = slp.id
                    where
                        sl.usage='internal'
                union
                    select
                        sl.id as loc_id, tp.top_parent_id
                    from
                        stock_location sl, top_parent tp
                    where
                        sl.usage='internal' and sl.location_id=tp.loc_id
            ), move_qties as (
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
                foo.move_id as id,
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
                union all
                    select distinct
                        sm.id as move_id,
                        sm.picking_id as picking_id
                    from
                        stock_move sm
                        left join stock_move smp on smp.move_dest_id = sm.id
                        left join stock_move sms on sm.split_from = sms.id
                        left join stock_move smps on smps.move_dest_id = sms.id
                    where
                        sm.state = 'waiting'
                        and sm.picking_type_id is not null
                        and (smp.state = 'done' or smps.state = 'done')
                union all
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
                                    and sq.location_id in (
                                        select loc_id from top_parent where top_parent_id=mq.location_id
                                    )
                                    and sq.product_id = mq.product_id)
            ) foo
        )
        """)


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    @api.one
    def do_detailed_transfer(self):
        super(stock_transfer_details, self.with_context(no_recompute=True)).do_detailed_transfer()

