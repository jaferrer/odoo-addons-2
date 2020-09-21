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
from openerp.addons.connector.unit.mapper import mapping
from openerp.addons.connector_prestashop.models.sale_order.common import OrderDiscountAdapter
from openerp.addons.connector_prestashop_catalog_manager.models.product_template.exporter \
    import ProductTemplateExportMapper

from openerp import fields, models
from ..backend import prestashop_1_7


@prestashop_1_7
class OrderCartRule(OrderDiscountAdapter):
    _model_name = 'prestashop.sale.order.line.discount'
    _prestashop_model = 'order_cart_rules'


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    feature_value_ids = fields.Many2many('product.feature.value', string=u"Caractéristiques")


class PrestashopProductTemplate(models.Model):
    _inherit = 'prestashop.product.template'

    low_stock_alert = fields.Integer(
        string='Low Stock Alert',
        default=1,
    )
    prestashop_state = fields.Integer(
        string='Prestashop State',
        default=1,
    )


@prestashop_1_7
class ProductTemplateExportMapperExtension(ProductTemplateExportMapper):
    _model_name = 'prestashop.product.template'

    direct = ProductTemplateExportMapper.direct + [
        ('low_stock_alert', 'low_stock_alert'),
        ('prestashop_state', 'state'),
    ]

    @mapping
    def associations(self, record):
        res = super(ProductTemplateExportMapperExtension, self).associations(record)
        binder_feature = self.binder_for('prestashop.product.feature')
        binder_feature_value = self.binder_for('prestashop.product.feature.value')
        res['associations']['product_features'] = {
            'product_feature': [{
                'id': binder_feature.to_backend(fv.feature_id.id),
                'id_feature_value': binder_feature_value.to_backend(fv.id),
            } for fv in record.feature_value_ids]
        }
        return res
