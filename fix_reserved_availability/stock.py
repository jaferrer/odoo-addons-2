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

from openerp import models, fields, api
from openerp.tools.float_utils import float_round


class FixReservedAvailabilityStockMove(models.Model):
    _inherit = 'stock.move'

    reserved_availability = fields.Float(compute='_get_reserved_availability')

    @api.multi
    @api.depends('reserved_quant_ids')
    def _get_reserved_availability(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move in self:
            move.reserved_availability = float_round(sum([quant.qty for quant in move.reserved_quant_ids]),
                                                     precision_digits=precision)
