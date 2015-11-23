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

from openerp import models, fields, api


class MergePolPurchaseOrderGroup(models.TransientModel):
    _inherit = 'purchase.order.group'

    merge_different_dates = fields.Boolean(string="Merge purchase order lines",
                                           help="It will merge the lines anyway. For instance, you could lose the "
                                                "differences in required dates or unit prices between lines of same "
                                                "product.", default=True)

    @api.multi
    def merge_orders(self):
        self.ensure_one()
        return super(MergePolPurchaseOrderGroup,
                     self.with_context(merge_different_dates=self.merge_different_dates)).merge_orders()


class MergePolPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def do_merge(self):
        result = super(MergePolPurchaseOrder, self).do_merge()
        for key in result.keys():
            order = self.env['purchase.order'].search([('id', '=', key)])
            if self.env.context.get('merge_different_dates'):
                lines = order.order_line
                while lines:
                    lines_current_product = lines.filtered(lambda l: l.product_id == lines[0].product_id)
                    lines = lines - lines_current_product
                    min_date_planned = min([l.date_planned for l in lines_current_product])
                    line_to_keep = lines_current_product.filtered(lambda l: l.date_planned == min_date_planned)
                    if len(line_to_keep) > 1:
                        line_to_keep = line_to_keep[0]
                    lignes_to_delete = lines_current_product.filtered(lambda l: l != line_to_keep)
                    line_to_keep.product_qty = line_to_keep.product_qty + sum([l.product_qty for l in lignes_to_delete])
                    lignes_to_delete.unlink()
            if result.get(key):
                merged_orders = self.env['purchase.order'].search([('id', 'in', result.get(key))], order='date_order')
                if merged_orders:
                    dict_fields_to_keep = {'payment_term_id': merged_orders[0].payment_term_id.id,
                                           'incoterm_id': merged_orders[0].incoterm_id.id}
                    if self.env.context.get('fields_to_keep'):
                        for field_name in self.env.context.get('fields_to_keep'):
                            field_value = getattr(merged_orders[0], field_name)
                            if hasattr(field_value, "id"):
                                field_value = field_value.id
                            dict_fields_to_keep[field_name] = field_value
        return result
