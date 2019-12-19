# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import math

from collections import defaultdict
from psycopg2 import OperationalError

from odoo.addons import decimal_precision as dp

from odoo import api, fields, models, registry
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round


class ProductSupplierInfoSchedulerImproved(models.Model):
    _inherit = 'product.supplierinfo'

    qty_multiple = fields.Float(
        u"Quantity Multiple", digits=dp.get_precision('Product Unit of Measure'),
        default=1, required=True,
        help="The minimum quantity will be rounded up to this multiple. If it is 0, the exact quantity will be used.")

    @api.model
    def find_best_supplier_moq_from_qty(self, product, qty, suppliers=None):
        best_diff = 0
        best_nb_multiple = 0
        best_qty = 0
        best_supplier = self.env['product.supplierinfo']
        first_psi = True

        domain_suppliers = [('product_id', '=', product.id)]

        if suppliers:
            domain_suppliers += [('id', 'in', suppliers.ids)]

        for psi in self.search(domain_suppliers, order='min_qty asc, price asc'):
            diff = qty - psi.min_qty
            nb_multiple = 0
            if diff > 0:
                nb_multiple = math.ceil(diff / (psi.qty_multiple or 1.0))
                final_qty = psi.min_qty + nb_multiple * (psi.qty_multiple or 1.0)
            else:
                final_qty = psi.min_qty
            final_diff = final_qty - qty

            if first_psi or final_diff <= best_diff and nb_multiple <= best_nb_multiple:
                if first_psi:
                    first_psi = False
                best_diff = final_diff
                best_nb_multiple = nb_multiple
                best_qty = final_qty
                best_supplier = psi

        return best_supplier, best_qty


class ProcurementOrderSchedulerImproved(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False):
        if company_id and self.env.user.company_id.id != company_id:
            self = self.with_context(company_id=company_id, force_company=company_id)

        order_point = self.env['stock.warehouse.orderpoint']
        domain = self._get_orderpoint_domain(company_id=company_id)
        orderpoints_noprefetch = order_point.with_context(prefetch_fields=False).search(
            domain, order=self._procurement_from_orderpoint_get_order()).ids
        while orderpoints_noprefetch:
            cr = False
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))
            order_point = self.env['stock.warehouse.orderpoint']
            procurement_list = []

            orderpoints = order_point.browse(orderpoints_noprefetch[:1000])
            orderpoints_noprefetch = orderpoints_noprefetch[1000:]

            # Calculate groups that can be executed together
            location_data = defaultdict(
                lambda: dict(products=self.env['product.product'], orderpoints=self.env['stock.warehouse.orderpoint'],
                             groups=list()))
            for orderpoint in orderpoints:
                key = self._procurement_from_orderpoint_get_grouping_key([orderpoint.id])
                location_data[key]['products'] += orderpoint.product_id
                location_data[key]['orderpoints'] += orderpoint
                location_data[key]['groups'] = self._procurement_from_orderpoint_get_groups([orderpoint.id])

            for _, location_data in location_data.iteritems():
                location_orderpoints = location_data['orderpoints']
                product_context = dict(self._context, location=location_orderpoints[0].location_id.id)
                substract_quantity = location_orderpoints.subtract_procurements_from_orderpoints()

                for group in location_data['groups']:
                    if group.get('from_date'):
                        product_context['from_date'] = group['from_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if group['to_date']:
                        product_context['to_date'] = group['to_date'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    product_quantity = location_data['products'].with_context(product_context)._product_available()
                    for orderpoint in location_orderpoints:
                        try:
                            self._create_procs(orderpoint, product_quantity, substract_quantity,
                                               group, use_new_cursor, cr, procurement_list)
                        except OperationalError:
                            if use_new_cursor:
                                orderpoints_noprefetch += [orderpoint.id]
                                cr.rollback()
                                continue
                            else:
                                raise

            try:
                # TDE CLEANME: use record set ?
                procurement_list.reverse()
                procurements = self.env['procurement.order']
                for proc in procurement_list:
                    procurements += proc
                procurements.run()
                if use_new_cursor:
                    cr.commit()
            except OperationalError:
                if use_new_cursor:
                    cr.rollback()
                    continue
                else:
                    raise

            if use_new_cursor:
                cr.commit()
                cr.close()

        return {}

    @api.model
    def _create_procs(self, orderpoint, product_qty, substract_qty, group, use_new_cursor, cr, proc_list):
        procurement = self.env['procurement.order']
        procurement_autorundefer = procurement.with_context(procurement_autorun_defer=True)

        op_product_virtual = product_qty[orderpoint.product_id.id]['virtual_available']
        if op_product_virtual is None:
            return
        if float_compare(op_product_virtual, orderpoint.product_min_qty,
                         precision_rounding=orderpoint.product_uom.rounding) < 0:
            qty = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - op_product_virtual

            _, qty = self.env['product.supplierinfo'].find_best_supplier_moq_from_qty(orderpoint.product_id, qty)

            if float_compare(qty, 0.0, precision_rounding=orderpoint.product_uom.rounding) < 0:
                return

            qty -= substract_qty[orderpoint.id]
            qty_rounded = float_round(qty, precision_rounding=orderpoint.product_uom.rounding)
            if qty_rounded > 0:
                new_procurement = procurement_autorundefer.create(
                    orderpoint._prepare_procurement_values(qty_rounded,
                                                           **group['procurement_values']))
                proc_list.append(new_procurement)
                new_procurement.message_post_with_view('mail.message_origin_link',
                                                       values={'self': new_procurement,
                                                               'origin': orderpoint},
                                                       subtype_id=self.env.ref('mail.mt_note').id)
                self._procurement_from_orderpoint_post_process([orderpoint.id])
            if use_new_cursor:
                cr.commit()

    @api.multi
    def _make_po_select_supplier(self, suppliers):
        self.ensure_one()
        psi, _ = self.env['product.supplierinfo'].find_best_supplier_moq_from_qty(
            self.product_id, self.product_qty, suppliers)
        return psi
