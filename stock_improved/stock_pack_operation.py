# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.cr_uid_id_context
    def _copy_remaining_pack_lot_ids(self, cr, uid, id, new_operation_id, context=None):
        return super(StockPackOperation, self)._copy_remaining_pack_lot_ids(cr, uid, id, new_operation_id, context=None)

    @api.multi
    def _set_product_qty_in_qty_done(self, unlink_if_zero=True):
        for rec in self:
            if rec.product_qty > 0:
                rec.qty_done = rec.product_qty
            elif unlink_if_zero:
                rec.unlink()
