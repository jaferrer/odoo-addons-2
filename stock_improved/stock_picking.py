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

from openerp import models, api, _
from openerp.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def get_data_for_new_package(self, for_packops=False):
        self.ensure_one()
        return {}

    @api.multi
    @api.returns('stock.quant.package')
    def put_in_pack(self):
        """
        This is a complete override of the function /odoo/addons/stock/stock.py#1732
        This override replace the odoo function with this improvement
        - New api style
        - Allow to give a custom dict in the create of the stock.quant.package
        :return: the new package id if one is created
        :rtype:int
        """
        package = self.env['stock.quant.package']
        for rec in self:
            operations = rec.pack_operation_ids.filtered(lambda it: it.qty_done > 0 and (not it.result_package_id))
            pack_operation = self.env["stock.pack.operation"]
            for operation in operations:
                # If we haven't done all qty in operation, we have to split into 2 operation
                op = operation
                if operation.qty_done < operation.product_qty:
                    new_operation = operation.copy({'product_qty': operation.qty_done, 'qty_done': operation.qty_done})
                    operation.write({'product_qty': operation.product_qty - operation.qty_done, 'qty_done': 0})
                    if operation.pack_lot_ids:
                        new_operation.write({'pack_lot_ids': [(4, x.id) for x in operation.pack_lot_ids]})
                        new_operation._copy_remaining_pack_lot_ids(operation)
                    op = new_operation
                pack_operation |= op
            if operations:
                pack_operation.check_tracking()
                package = self.env['stock.quant.package'].create(rec.get_data_for_new_package(pack_operation))
                pack_operation.write({'result_package_id': package.id})
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package

    @api.multi
    def fill_all_pack_operation(self, unlink_if_zero=True):
        for rec in self:
            rec.pack_operation_ids._set_product_qty_in_qty_done(unlink_if_zero)
