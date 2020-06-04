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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import ImportMapper, mapping
from openerp.addons.connector_prestashop.unit.importer import TranslatableRecordImporter, DelayedBatchImporter

from ...backend import prestashop_1_7


@prestashop_1_7
class FeatureMapper(ImportMapper):
    _model_name = 'prestashop.product.feature'

    direct = [
        ('name', 'name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@prestashop_1_7
class FeatureValueMapper(ImportMapper):
    _model_name = 'prestashop.product.feature.value'

    direct = [
        ('value', 'name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def feature_id(self, record):
        if record['id_feature'] == '0':
            return {}
        feature = self.binder_for('prestashop.product.feature').to_odoo(
            record['id_feature'], unwrap=True)
        return {
            'feature_id': feature.id,
        }


@prestashop_1_7
class ProductFeatureImporter(TranslatableRecordImporter):
    _model_name = [
        'prestashop.product.feature',
    ]
    _base_mapper = FeatureMapper
    _translatable_fields = {
        'prestashop.product.feature': ['name'],
    }


@prestashop_1_7
class ProductFeatureValueImporter(TranslatableRecordImporter):
    _model_name = [
        'prestashop.product.feature.value',
    ]
    _base_mapper = FeatureValueMapper
    _translatable_fields = {
        'prestashop.product.feature.value': ['value'],
    }

    def _import_dependencies(self):
        record = self.prestashop_record
        if record['id_feature'] == '0':
            return

        self._import_dependency(record['id_feature'], 'prestashop.product.feature')


@prestashop_1_7
class ProductFeatureValueBatchImporter(DelayedBatchImporter):
    _model_name = 'prestashop.product.feature.value'


@job(default_channel='root.prestashop')
def import_features(session, backend_id):
    backend = session.env['prestashop.backend'].browse(backend_id)
    env = backend.get_environment('prestashop.product.feature.value', session=session)
    feature_value_importer = env.get_connector_unit(ProductFeatureValueBatchImporter)
    return feature_value_importer.run()
