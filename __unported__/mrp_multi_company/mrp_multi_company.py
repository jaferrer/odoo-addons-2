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

from openerp import fields, models, api, exceptions, _


# Ajout de champs à la table mrp.production
class MrpProduction(models.Model):
    _inherit = "mrp.production"

    def _get_sale_ref(self, cr, uid, ids, field_name=False):
        move_obj = self.pool.get('stock.move')

        def get_parent_move(move_id):
            move = move_obj.browse(cr, uid, move_id)
            if move.move_dest_id:
                return get_parent_move(move.move_dest_id.id)
            return move_id

        res = {}
        productions = self.browse(cr, uid, ids)
        for production in productions:
            res[production.id] = False
            if production.move_prod_id:
                try:
                    parent_move_line = get_parent_move(production.move_prod_id.id)
                    if parent_move_line:
                        move = move_obj.browse(cr, uid, parent_move_line)
                        if field_name == 'name':
                            res[production.id] = move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.name or False
                        if field_name == 'client_order_ref':
                            res[production.id] = move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.client_order_ref or False
                except exceptions.AccessError:
                    pass
        return res
