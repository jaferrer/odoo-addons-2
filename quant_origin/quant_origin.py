# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class QuantOriginStockQuant(models.Model):
    _inherit = 'stock.quant'

    origin = fields.Char(string='Quant origin', readonly=True)

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        created_quant = super(QuantOriginStockQuant, self)._quant_create(qty, move, lot_id=lot_id, owner_id=owner_id,
                                                                          src_package_id=src_package_id,
                                                                          dest_package_id=dest_package_id,
                                                                          force_location_from=force_location_from,
                                                                          force_location_to=force_location_to)
        created_quants = created_quant + created_quant.propagated_from_id
        created_quants.sudo().write({'origin': move.origin})
        return created_quant
