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

from openerp.addons.connector_prestashop.models.account_invoice.importer import RefundMapper


from ..backend import prestashop_1_7


@prestashop_1_7
class RefundMapperExtension(RefundMapper):
    _model_name = 'prestashop.refund'

    def _invoice_line(self, record, fpos):
        order_line = self._get_order_line(record['id_order_detail'])
        tax_ids = []
        if order_line is None:
            product_id = None
            name = "Order line not found"
            account_id = None
        else:
            product = order_line.product_id
            product_id = product.id
            name = order_line.name
            for tax in order_line.tax_id:
                tax_ids.append(tax.id)
            account_id = product.property_account_income_id.id
            if not account_id:
                categ = product.categ_id
                account_id = categ.property_account_income_categ_id.id
        if fpos and account_id:
            fpos_obj = self.session.pool['account.fiscal.position']
            account_id = fpos_obj.map_account(
                self.session.cr,
                self.session.uid,
                fpos,
                account_id
            )
        if record['product_quantity'] == '0':
            quantity = 1
        else:
            quantity = record['product_quantity']

        if tax_ids and self.env['account.tax'].browse(tax_ids[0]).price_include:
            price_unit = record['amount_tax_incl']
        else:
            price_unit = record['amount_tax_excl']

        try:
            price_unit = float(price_unit) / float(quantity)
        except ValueError:
            pass

        discount = False
        if price_unit in ['0.00', ''] and order_line is not None:
            price_unit = order_line['price_unit']
            discount = order_line['discount']
        return {
            'quantity': quantity,
            'product_id': product_id,
            'name': name,
            'invoice_line_tax_ids': [(6, 0, tax_ids)],
            'price_unit': price_unit,
            'discount': discount,
            'account_id': account_id,
        }
