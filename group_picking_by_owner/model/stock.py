# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    group_picking_by_owner = fields.Boolean(u"Group picking by owner")


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def _get_stock_picking_query(self):
        """ If the stock.picking.type has `group_picking_by_owner`, restricts the stock.picking search to picking with
        same owner as this move
        """
        picking_type = self[0].picking_type_id
        query, params = super(StockMove, self)._get_stock_picking_query()
        if picking_type.group_picking_by_owner:
            query += " AND sp.owner_id = %s"
            params += (self[0].restrict_partner_id.id, )
        return query, params

    @api.model
    def _prepare_picking_assign(self, move):
        """ Add the owner of the move to the values used to create the new stock.picking """
        values = super(StockMove, self)._prepare_picking_assign(move)
        values['owner_id'] = move.restrict_partner_id and move.restrict_partner_id.id or False
        return values
