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

from openerp import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.one
    def move_to(self, dest_location):
        move_obj = self.env['stock.move']
        new_move = move_obj.create({
            'name': 'Move %s to %s' % (self.product_id.name,
                                       dest_location.name),
            'product_id': self.product_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': dest_location.id,
            'product_uom_qty': self.qty,
            'product_uom': self.product_id.uom_id.id,
            'date_expected': fields.Datetime.now(),
            'date': fields.Datetime.now(),
            'quant_ids': [(4, self.id)]
        })
        new_move.action_done()