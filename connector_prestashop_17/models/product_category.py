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

from openerp.addons.connector.unit.mapper import backend_to_m2o
from openerp.addons.connector_prestashop.models.product_category.importer \
    import ProductCategoryMapper
from openerp.addons.connector_prestashop_catalog_manager.models.product_category.exporter \
    import ProductCategoryExportMapper

from openerp import fields, models
from ..backend import prestashop_1_7


class PrestashopProductCategory(models.Model):
    _inherit = 'prestashop.product.category'

    prestashop_active = fields.Boolean(u"Active on prestashop", default=True)


@prestashop_1_7
class ProductCategoryMapperExtension(ProductCategoryMapper):
    _model_name = 'prestashop.product.category'

    direct = [
        ('position', 'sequence'),
        ('description', 'description'),
        ('link_rewrite', 'link_rewrite'),
        ('meta_description', 'meta_description'),
        ('meta_keywords', 'meta_keywords'),
        ('meta_title', 'meta_title'),
        (backend_to_m2o('id_shop_default'), 'default_shop_id'),
        ('active', 'prestashop_active'),
        ('position', 'position')
    ]


@prestashop_1_7
class ProductCategoryExportMapperExtension(ProductCategoryExportMapper):
    _model_name = 'prestashop.product.category'

    direct = [
        ('sequence', 'position'),
        ('default_shop_id', 'id_shop_default'),
        ('prestashop_active', 'active'),
        ('position', 'position')
    ]
