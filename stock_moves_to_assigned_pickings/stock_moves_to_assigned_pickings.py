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
    def _picking_assign(self):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group,
        location_from and location_to (and company). Those attributes are also given as parameters.
        """
        if len(self) == 0:
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