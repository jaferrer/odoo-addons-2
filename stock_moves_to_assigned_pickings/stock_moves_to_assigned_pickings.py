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

from openerp import models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_confirm(self):
        """ Full override of action_confirm to open this method + re-write in new style
        _get_key_to_assign_move_to_picking = to customize how a move is grouped before assigning in a picking
        """
        states = {
            'confirmed': self.env['stock.move'],
            'waiting': self.env['stock.move'],
        }
        to_assign = {}
        for rec in self:
            self.env['stock.move'].attribute_price(rec)
            state = 'confirmed'
            #if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if rec.move_orig_ids:
                state = 'waiting'
            #if the move is split and some of the ancestor was preceeded, then it's waiting as well
            elif rec.split_from:
                move2 = rec.split_from
                while move2 and state != 'waiting':
                    if move2.move_orig_ids:
                        state = 'waiting'
                    move2 = move2.split_from
            states[state] |= rec

            if not rec.picking_id and rec.picking_type_id:
                key = rec._get_key_to_assign_move_to_picking()
                to_assign.setdefault(key, self.env['stock.move'])
                to_assign[key] |= rec
        moves = states['confirmed'].filtered(lambda move: move.procure_method == 'make_to_order')
        self.env['stock.move']._create_procurements(moves)

        for move in moves:
            states['waiting'] |= move
            states['confirmed'] |= move

        for state, to_writes in states.items():
            if to_writes:
                to_writes.write({'state': state})
        #assign picking in batch for all confirmed move that share the same details
        for move_to_assign in to_assign.values():
            move_to_assign._picking_assign()

        self.env['stock.move']._push_apply(self)
        return self.ids

    @api.multi
    def _get_key_to_assign_move_to_picking(self):
        self.ensure_one()
        return (self.group_id.id, self.location_id.id, self.location_dest_id.id)

    @api.multi
    def _picking_assign(self):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group,
        location_from and location_to (and company). Those attributes are also given as parameters.
        """
        if not self:
            return True

        # Allow to extend easily this method, by adding parts to the request, and the according parameters
        query, params = self._get_stock_picking_query()
        self.env.cr.execute(query + " LIMIT 1", params)
        pick_id = (self.env.cr.fetchone() or [None])[0]
        if not pick_id:
            move = self[0]
            values = self._prepare_picking_assign(move)
            pick = self.env['stock.picking'].create(values)
            pick_id = pick.id
        pick_list = self.env.context.get('only_pickings')
        if pick_list and pick_id not in pick_list:
            # Don't assign the move to a picking that is not our picking.
            return True
        return self.with_context(mail_notrack=True).write({'picking_id': pick_id})

    @api.multi
    def _get_stock_picking_query(self):
        """ Return both the query and parameters to get a correct stock.picking for this or these stock.move(s) """
        procurement_group = self[0].group_id
        location_from = self[0].location_id
        location_to = self[0].location_dest_id
        picking_type = self[0].picking_type_id
        # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
        # In the next version, the locations on the picking should be stored again.
        query = """
            SELECT sp.id
            FROM stock_move AS sm
            INNER JOIN stock_picking AS sp ON sp.id = sm.picking_id
            WHERE
                sp.state IN ('draft','waiting','confirmed','partially_available','assigned') AND
                sp.picking_type_id = %s AND
                sm.location_id = %s AND
                sm.location_dest_id = %s AND
        """
        params = (picking_type.id, location_from.id, location_to.id)
        if not procurement_group:
            query += "sp.group_id IS NULL"
        else:
            query += "sp.group_id = %s"
            params += (procurement_group.id,)

        return query, params