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

from decimal import Decimal

from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.connector_prestashop.models.sale_order.importer import \
    SaleOrderLineMapper, SaleOrderLineDiscountMapper, SaleOrderImporter

from ..backend import prestashop_1_7


@prestashop_1_7
class SaleOrderImporterExtension(SaleOrderImporter):
    _model_name = ['prestashop.sale.order']

    def _add_shipping_line(self, binding):
        taxes = binding.odoo_id.carrier_id.product_id.taxes_id
        tax_included = taxes and taxes.price_include or False
        shipping_total = (binding.total_shipping_tax_included
                          if tax_included
                          else binding.total_shipping_tax_excluded)
        # when we have a carrier_id, even with a 0.0 price,
        # Odoo will adda a shipping line in the SO when the picking
        # is done, so we better add the line directly even when the
        # price is 0.0
        if binding.odoo_id.carrier_id:
            binding.odoo_id._create_delivery_line(
                binding.odoo_id.carrier_id,
                shipping_total
            )
        binding.odoo_id.recompute()


@prestashop_1_7
class SaleOrderLineMapperExtension(SaleOrderLineMapper):
    _model_name = 'prestashop.sale.order.line'

    @mapping
    def price_unit(self, record):
        taxes = self._get_taxes(record)
        if taxes and taxes[0].price_include:
            key = 'unit_price_tax_incl'
        else:
            key = 'unit_price_tax_excl'
        if record['reduction_percent']:
            reduction = Decimal(record['reduction_percent'])
            price = Decimal(record[key])
            price_unit = price / ((100 - reduction) / 100)
        else:
            price_unit = record[key]
        return {'price_unit': price_unit}

    def _get_taxes(self, record):
        taxes = record.get('associations', {}).get('taxes', {}).get(
            self.backend_record.get_version_ps_key('tax'), [])
        if not isinstance(taxes, list):
            taxes = [taxes]
        result = self.env['account.tax'].browse()
        for ps_tax in taxes:
            result |= self._find_tax(ps_tax['id'])
        return result


@prestashop_1_7
class SaleOrderLineDiscountMapperExtension(SaleOrderLineDiscountMapper):
    _model_name = 'prestashop.sale.order.line.discount'

    @mapping
    def price_unit(self, record):
        taxes = self.backend_record.discount_product_id.taxes_id
        tax_included = taxes and taxes.price_include or False
        if tax_included:
            price_unit = record['value']
        else:
            price_unit = record['value_tax_excl']
        if price_unit[0] != '-':
            price_unit = '-' + price_unit
        return {'price_unit': price_unit}
