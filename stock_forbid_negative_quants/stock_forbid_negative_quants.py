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

from openerp import models, api, exceptions, _
from openerp.tools import config


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        if not config["test_enable"] and move.location_id.usage == 'internal':
            raise exceptions.except_orm(
                _("Error !"),
                _("You are not allowed to move products quants that are not available. "
                  "If the quants are available, check that package, owner and lot no. match. "
                  "Product: %s, Missing qty: %s, Location: %s, Lot: %s, Package: %s") % (
                    move.product_id.default_code,
                    qty,
                    move.location_id.complete_name,
                    lot_id and self.env['stock.production.lot'].browse(lot_id).name or "-",
                    src_package_id and self.env['stock.quant.package'].browse(src_package_id).name or "-",
                )
            )
        return super(StockQuant, self)._quant_create(qty, move, lot_id, owner_id, src_package_id, dest_package_id,
                                                     force_location_from, force_location_to)
