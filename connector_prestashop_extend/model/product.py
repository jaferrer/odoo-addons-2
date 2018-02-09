# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import base64
import logging
from datetime import datetime
import urllib2
import xmlrpclib
import csv
import StringIO
import datetime as dt
import ftputil
import ftputil.session
import sys

from openerp import tools

try:
    from xml.etree import cElementTree as ElementTree
except ImportError, e:
    from xml.etree import ElementTree

from openerp.addons.connector.connector import ConnectorUnit, Binder
from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.exception import (JobError, RetryableJobError)
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.unit.synchronizer import (Importer, Exporter
                                                        )

from openerp import models, fields, api
from openerp.tools import float_compare
from ..backend import prestashopextend
from ..connector import get_environment
from ..unit.backend_adapter import (GenericAdapter, prestashopextendCRUDAdapter)
from ..unit.importer import (DelayedBatchImporter, TranslatableRecordImporter,import_batch, RETRY_ON_ADVISORY_LOCK, RETRY_WHEN_CONCURRENT_DETECTED)

_logger = logging.getLogger(__name__)

try:
    from prestapyt import PrestaShopWebServiceError
except ImportError:
    _logger.debug('Can not `from prestapyt import PrestaShopWebServiceError`.')


_logger = logging.getLogger(__name__)


class PrestashopProductCombination(models.Model):
    _name = 'prestashopextend.product.product'
    _inherit = 'prestashopextend.binding.odoo'
    _inherits = {'product.product': 'openerp_id'}

    openerp_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        ondelete='cascade',
        oldname='openerp_id',
    )
    backend_id = fields.Many2one(
        comodel_name='prestashopextend.backend',
        string='prestashopextend Backend',
        store=True,
        readonly=False,
    )

    backend_home_id = fields.Many2one(
        related='backend_id.connector_id.home_id',
        comodel_name='backend.home',
        string='Backend Home',
        store=True,
        required=False,
        ondelete='restrict',
    )

    updated_at = fields.Datetime(string='Updated At (on Prestashop)',
                                 readonly=True)


@prestashopextend
class ProductCombinationAdapter(GenericAdapter):
    _model_name = 'prestashopextend.product.product'
    _prestashopextend_model = 'products'
    _export_node_name = 'product'


@prestashopextend
class ProductCombinationRecordImport(TranslatableRecordImporter):
    _model_name = 'prestashopextend.product.product'

    _translatable_fields = {
        'prestashopextend.product.product': [
            'name',
            'description',
            'link_rewrite',
            'description_short',
            'meta_title',
            'meta_description',
            'meta_keywords',
        ],
    }

    def has_combinations(self, record):
        combinations = record.get('associations', {}).get(
            'combinations', {}).get('combination', [])
        return combinations

    def get_reccord_presta(self, id, model):
        res = self.backend_adapter.client.get(model, id, options=None)
        first_key = res.keys()[0]
        return res[first_key]

    def has_combinations_options_values(self, record):
        combinations = record.get('associations', {}).get(
            'product_option_values', {}).get('product_option_value', [])
        return combinations

    def run(self, prestashopextend_id, **kwargs):
        """ Run the synchronization

        :param magentoextend_id: identifier of the record on magentoextendCommerce
        """
        self.prestashopextend_id = prestashopextend_id
        lock_name = 'import({}, {}, {}, {})'.format(
            self.backend_record._name,
            self.backend_record.id,
            self.model._name,
            self.prestashopextend_id,
        )
        # Keep a lock on this import until the transaction is committed
        self.advisory_lock_or_retry(lock_name,
                                    retry_seconds=RETRY_ON_ADVISORY_LOCK)
        self.prestashopextend_record = self._get_prestashopextend_data()
        prestashop_products = []
        combinations = self.has_combinations(self.prestashopextend_record)
        if combinations:
            for comb in combinations:
                prestashop_product = self.prestashopextend_record.copy()
                rec_comb = self.get_reccord_presta(comb.get("id"), "combinations")
                prestashop_product["id"] = "%s_%s" % (prestashop_product.get("id"), comb.get("id"))
                prestashop_product["reference_combination"] = comb.get("id")
                option_values = self.has_combinations_options_values(rec_comb)
                if not isinstance(option_values, list):
                    option_values = [option_values]
                    name_att = ""
                    for opt_value in option_values:
                        rec_opt = self.get_reccord_presta(opt_value.get("id"), "product_option_values")
                        list_name = rec_opt.get("name", {}).get('language', [])
                        if list_name:
                            name_att = "%s - ATTR : %s" % (name_att, list_name[0].get("value"))
                    prestashop_product["name_comb"] = name_att
                prestashop_products.append(prestashop_product)
        else:
            prestashop_products.append(self.prestashopextend_record)

        for prest_record in prestashop_products:
            self.prestashopextend_id = prest_record.get("id")
            self.prestashopextend_record = prest_record
            binding = self._get_binding()
            if not binding:
                with self.do_in_new_connector_env() as new_connector_env:
                    binder = new_connector_env.get_connector_unit(Binder)
                    if binder.to_openerp(self.prestashopextend_id):
                        raise RetryableJobError(
                            'Concurrent error. The job will be retried later',
                            seconds=RETRY_WHEN_CONCURRENT_DETECTED,
                            ignore_retry=True
                        )
            skip = self._has_to_skip()
            if skip:
                return skip

            self._import(binding, **kwargs)


@prestashopextend
class ProductProductImportMapper(ImportMapper):
    _model_name = 'prestashopextend.product.product'

    direct = [('name', 'name'),
              ('description', 'description'),
              ('weight', 'weight'),
              ('wholesale_price', 'standard_price')
              ]

    @mapping
    def is_active(self, record):
        # return {'active': (record.get('status') == '1')}
        return {'active': True}

    @mapping
    def price(self, record):
        """ The price is imported at the creation of
        the product, then it is only modified and exported
        from OpenERP """
        return {'list_price': record.get('price', 0.0)}

    @mapping
    def name(self, record):
        name = 'noname'
        if record['name']:
            name = record['name']

        if self.has_combinations(record):
            name = "%s%s" % (name, record.get("name_comb"))

        return {'name': name}

    @mapping
    def prestashopextend_id(self, record):
        return {'prestashopextend_id': record['id']}

    @mapping
    def date_upd(self, record):
        if record['date_upd'] == '0000-00-00 00:00:00':
            return {'updated_at': datetime.now()}
        return {'updated_at': record['date_upd']}

    def has_combinations(self, record):
        combinations = record.get('associations', {}).get(
            'combinations', {}).get('combination', [])
        return len(combinations) != 0

    def _template_code_exists(self, code):
        model = self.session.env['product.template']
        template_ids = model.search([
            ('default_code', '=', code),
            ('company_id', '=', self.backend_record.company_id.id),
        ], limit=1)

        return len(template_ids) > 0

    @mapping
    def default_code(self, record):
        code = record.get('reference')
        if not code:
            code = "backend_%d_product_%s" % (
                self.backend_record.connector_id.home_id.id, record['id']
            )
        if self.has_combinations(record):
            code = "%s-%s" % (code, record.get("reference_combination"))
        return {'default_code': code}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def owner_id(self, record):
        return {'owner_id': self.backend_record.connector_id.home_id.partner_id.id}

    @mapping
    def type(self, record):
        return {"type": 'product'}


@prestashopextend
class ProductInventoryAdapter(GenericAdapter):
    _model_name = '_import_stock_available'
    _prestashopextend_model = 'stock_availables'
    _export_node_name = 'stock_available'

    def get(self, options=None):
        return self.client.get(self._prestashopextend_model, options=options)

    def export_quantity(self, filters, quantity):
        self.export_quantity_url(
            filters,
            quantity,
        )

        # shops = self.env['prestashop.shop'].search([
        #     ('backend_id', '=', self.backend_record.id),
        #     ('default_url', '!=', False),
        # ])
        # for shop in shops:
        #     url = '%s/api' % shop.default_url
        #     key = self.backend_record.webservice_key
        #     client = PrestaShopWebServiceDict(url, key)
        #     self.export_quantity_url(filters, quantity, client=client)

    def export_quantity_url(self, filters, quantity, client=None):
        if client is None:
            client = self.client
        response = client.search(self._prestashopextend_model, filters)
        for stock_id in response:
            res = client.get(self._prestashopextend_model, stock_id)
            first_key = res.keys()[0]
            stock = res[first_key]
            stock['quantity'] = int(quantity)
            try:
                client.edit(
                    self._prestashopextend_model, {self._export_node_name: stock})
            # TODO: investigate the silent errors
            except PrestaShopWebServiceError:
                pass
            except ElementTree.ParseError:
                pass


@prestashopextend
class StockLevelExporter(Exporter):
    _model_name = 'prestashopextend.product.product'

    def run(self):
        log = ""

        self.env.cr.execute(""" WITH RECURSIVE top_parent(loc_id, top_parent_id) AS (
            SELECT
              sl.id AS loc_id,
              sl.id AS top_parent_id
            FROM
              stock_location sl
              LEFT JOIN stock_location slp ON sl.location_id = slp.id
            WHERE
              sl.usage = 'internal'
            UNION
            SELECT
              sl.id AS loc_id,
              tp.top_parent_id
            FROM
              stock_location sl, top_parent tp
            WHERE
              sl.usage = 'internal' AND sl.location_id = tp.loc_id
          )
          select
          product_id,
          prestashopextend_id,
          default_code,
          sum(qty) qty
          from (
          SELECT
               sq.product_id,
               mpp.prestashopextend_id,
               pp.default_code,
               sum(sq.qty) qty
             FROM
               stock_quant sq
               LEFT JOIN prestashopextend_product_product mpp ON mpp.openerp_id = sq.product_id
               LEFT JOIN product_product pp ON mpp.openerp_id = pp.id
               LEFT JOIN top_parent tp ON tp.loc_id = sq.location_id
               LEFT JOIN stock_location sl ON sl.id = tp.top_parent_id
             where mpp.backend_home_id = %s and sl.id =%s
             GROUP BY
               sq.product_id,
               mpp.prestashopextend_id,
               pp.default_code

            union ALL

            SELECT
               pp.id,
               mpp.prestashopextend_id,
               pp.default_code,
               0 qty
            FROM
               prestashopextend_product_product mpp
               LEFT JOIN product_product pp ON mpp.openerp_id = pp.id
            where mpp.backend_home_id = %s) rqx
            group by
            product_id,
            prestashopextend_id,
            default_code
                    """, (self.backend_record.connector_id.home_id.id,
                          self.backend_record.connector_id.home_id.warehouse_id.lot_stock_id.id,
                          self.backend_record.connector_id.home_id.id
                          ))

        log = ""

        export = False

        for product in self.env.cr.dictfetchall():
            export = True
            qty = int(product['qty'])
            log += "\n%s : %s\n" % (product['prestashopextend_id'], str(qty))
            if float_compare(product['qty'], 0, 1) <= 0:
                qty = int(0)
            if product['prestashopextend_id']:
                adapter = self.unit_for(GenericAdapter, '_import_stock_available')
                filter = {
                    'filter[id_product]': product['prestashopextend_id'].split('_')[0],
                    'filter[id_product_attribute]': len(product['prestashopextend_id'].split('_')) > 1 and product['prestashopextend_id'].split('_')[1] or 0
                }
                adapter.export_quantity(filter, qty)

        return log


@prestashopextend
class ProductProductBatchImporter(DelayedBatchImporter):
    _model_name = 'prestashopextend.product.product'
    _prestashopextend_model = 'products'


@job(default_channel='root.prestashopextend_pull_product_product')
def product_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of product modified on magentoextend """
    if filters is None:
        filters = {}
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(ProductProductBatchImporter)
    importer.run(filters=filters)


@job(default_channel='root.prestashopextend_push_product_level')
def product_export_stock_level_batch(session, model_name, backend_id, filters=None):
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(StockLevelExporter)
    importer.run()


class ResPartnerBackend(models.Model):
    _inherit = 'product.product'

    owner_id = fields.Many2one('res.partner', string=u"Owner")
