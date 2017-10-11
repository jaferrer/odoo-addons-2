# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def _make_merge_key(self):
        self.ensure_one()
        return self.partner_id.id, self.picking_type_id.id, self.currency_id.id

    @api.multi
    def do_merge(self):
        """
        To merge similar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist, same currency
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @return: new purchase order id

        """
        # Compute what the new orders should contain
        new_orders = {}
        order_lines_to_move = {}

        for porder in self.filtered(lambda p: p.state == 'draft'):
            order_key = porder._make_merge_key()
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            order_lines_to_move.setdefault(order_key, [])

            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date_order': porder.date_order,
                    'partner_id': porder.partner_id.id,
                    'dest_address_id': porder.dest_address_id.id,
                    'picking_type_id': porder.picking_type_id.id,
                    'currency_id': porder.currency_id.id,
                    'state': 'draft',
                    'order_line': {},
                    'notes': '%s' % (porder.notes or '',),
                    'fiscal_position_id': porder.fiscal_position_id and porder.fiscal_position_id.id or False,
                })
            else:
                if porder.date_order < order_infos['date_order']:
                    order_infos['date_order'] = porder.date_order
                if porder.notes:
                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
                if porder.origin:
                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

            order_lines_to_move[order_key] += [order_line.id for order_line in porder.order_line
                                               if order_line.state != 'cancel']

        allorders = []
        orders_info = {}
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or [])
                continue

            # cleanup order line data
            for key, value in order_data['order_line'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            order_data['order_line'] = [(6, 0, order_lines_to_move[order_key])]

            # create the new order
            neworder = self.create(order_data)
            neworder.with_context(mail_create_nolog=True).message_post(body=_("RFQ created"))
            orders_info.update({neworder.id: old_ids})
            allorders.append(neworder.id)

            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                self.browse(old_id).button_cancel()

        return orders_info
