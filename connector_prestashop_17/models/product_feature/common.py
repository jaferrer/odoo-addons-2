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

from openerp.addons.connector_prestashop.unit.backend_adapter import GenericAdapter

from openerp import fields, models
from ...backend import prestashop_1_7


class ProductFeature(models.Model):
    _name = 'product.feature'
    _order = 'name'

    name = fields.Char(u"Nom", required=True, translate=True)
    value_ids = fields.One2many('product.feature.value', 'feature_id', string=u"Valeurs")


class ProductFeatureValue(models.Model):
    _name = 'product.feature.value'
    _order = 'feature_name, name'

    name = fields.Char(u"Nom", required=True, translate=True)
    feature_name = fields.Char(string=u"Nom de la caractéristique", related='feature_id.name', store=True)
    feature_id = fields.Many2one('product.feature', string=u"Caractéristique")


class PrestashopProductFeature(models.Model):
    _name = 'prestashop.product.feature'
    _inherit = 'prestashop.binding.odoo'
    _inherits = {'product.feature': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='product.feature',
        string=u"Caractéristique",
        required=True,
        ondelete='cascade',
    )


class PrestashopProductFeatureValue(models.Model):
    _name = 'prestashop.product.feature.value'
    _inherit = 'prestashop.binding.odoo'
    _inherits = {'product.feature.value': 'odoo_id'}

    odoo_id = fields.Many2one(
        comodel_name='product.feature.value',
        string=u"Valeur",
        required=True,
        ondelete='cascade',
    )


@prestashop_1_7
class ProductFeatureAdapter(GenericAdapter):
    _model_name = 'prestashop.product.feature'
    _prestashop_model = 'product_features'
    _export_node_name = 'product_feature'


@prestashop_1_7
class ProductFeatureValueAdapter(GenericAdapter):
    _model_name = 'prestashop.product.feature.value'
    _prestashop_model = 'product_feature_values'
    _export_node_name = 'product_feature_value'
