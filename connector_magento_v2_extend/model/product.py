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
import urllib2
import xmlrpclib
import csv
import StringIO
import datetime as dt
import ftputil
import ftputil.session
import sys

from openerp import tools

from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.exception import (JobError)
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )
from openerp.addons.connector.unit.synchronizer import (Importer, Exporter
                                                        )

from openerp import models, fields, api, _
from openerp.tools import float_compare
from openerp.addons.connector_magento_extend.backend import magentoextend
from ..connector import get_environment
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.import_synchronizer import (DelayedBatchImporterV2, magentoextendImporterV2)
from ..unit.mapper import normalize_datetime
from ..related_action import link

_logger = logging.getLogger(__name__)


class magentoextendProductProductv2(models.Model):
    _name = 'magentoextend2.product.product'
    _inherit = 'magentoextend.binding'
    _inherits = {'product.product': 'openerp_id'}
    _description = '2 product product'

    _rec_name = 'name'

    @api.model
    def product_type_get(self):
        return [
            ('simple', 'Simple Product'),
            ('configurable', 'Configurable Product'),
            # XXX activate when supported
            # ('grouped', 'Grouped Product'),
            # ('virtual', 'Virtual Product'),
            # ('bundle', 'Bundle Product'),
            # ('downloadable', 'Downloadable Product'),
        ]

    openerp_id = fields.Many2one(comodel_name='product.product',
                                 string='product',
                                 required=True,
                                 ondelete='cascade')

    backend_id = fields.Many2one(
        comodel_name='magentoextend.backend',
        string='magentoextend Backend',
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

    product_type = fields.Selection(selection='product_type_get',
                                    string='Magento Product Type',
                                    default='simple',
                                    required=True)

    slug = fields.Char('Slung Name')
    created_at = fields.Date('created_at')
    weight = fields.Float('weight')
    updated_at = fields.Datetime(string='Updated At (on Magento)',
                                 readonly=True)


@magentoextend
class ProductProductAdapter(GenericAdapter):
    _model_name = 'magentoextend2.product.product'
    _magentoextend_model = 'products'

    def update(self, el_id, arguments):
        return self._call('%s.update' % "cataloginventory_stock_item",
                          [el_id,arguments])

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        magentoextend_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        dt_fmt = magentoextend_DATETIME_FORMAT
        if from_date is not None:
            # updated_at include the created records
            filters['searchCriteria[filter_groups][0][filters][0][field]'] = 'updated_at'
            filters['searchCriteria[filter_groups][0][filters][0][condition_type]'] = 'gteq'
            filters['searchCriteria[filter_groups][0][filters][0][value]'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters['searchCriteria[filter_groups][1][filters][0][field]'] = 'updated_at'
            filters['searchCriteria[filter_groups][1][filters][0][condition_type]'] = 'lteq'
            filters['searchCriteria[filter_groups][1][filters][0][value]'] = to_date.strftime(dt_fmt)
        filters['searchCriteria[pageSize]'] = 100
        filters['searchCriteria[currentPage]'] = 1
        products_resp = []
        current_size = 0
        while 1:
            items = self._call('%s' % self._magentoextend_model, filters)
            list_size = items.get("total_count")
            if items.get("items"):
                current_size += len(items.get("items"))
                products_resp.extend(items.get("items"))
                filters['searchCriteria[currentPage]'] = filters['searchCriteria[currentPage]'] + 1
            if current_size >= list_size:
                break

        if products_resp:
            return [int(row['id']) for row in products_resp]
        return products_resp


    def read(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}

        items = self._call('%s' % self._magentoextend_model, filters)
        return items

    def get_images(self, id, storeview_id=None):
        return self._call('products/%s/media' % (id), {})

    def read_image(self, id, image_name, storeview_id=None):
        return self._call('catalog_product_attribute_media.info',
                          [int(id), image_name])

    def _callwrite_ftp(self, filename, content):
        _logger.info('Start creation of the file on the FTP server')
        backend = self.backend_record
        param = self.env[backend.connector_id.line_id.type_id.model_name].search(
            [('line_id', '=', backend.connector_id.line_id.id)])
        if not param.target_path:
            raise JobError('FTP target path to be filled in settings')
        target = param.target_path
        host = param.url
        user = param.user
        pasw = param.pwd

        # Raise a JobError if some fields are empty
        if not (host and user):
            raise JobError('FTP Host and User have to be filled in settings')

        _logger.debug('Try to connect FTP server %s with login %s', host, user)
        ftp_session_factory = ftputil.session.session_factory(use_passive_mode=False)
        with ftputil.FTPHost(host, user, pasw, session_factory=ftp_session_factory) as ftp_session:
            targetfile = '%s/%s' % (target, filename)
            with ftp_session.open(targetfile, 'w') as awa_file:
                awa_file.write(content.decode('utf8'))

        return 'STK file has been written to %s on host %s' % (targetfile, host)

    def _callwrite_local(self, filename, content):
        _logger.info('Start creation of the file on the local')

        backend = self.backend_record

        param = self.env[backend.connector_id.line_id.type_id.model_name].search(
            [('line_id', '=', backend.connector_id.line_id.id)])

        if not param.target_path:
            raise JobError('local target path to be filled in settings')
        target = param.target_path

        targetfile = '%s/%s' % (target, filename)
        with open(targetfile, 'w') as awa_file:
            awa_file.write(content)

        return 'STK file has been written to %s' % (targetfile)

    def write(self, filename, content):
        record = ""
        if self.backend_record.connector_id.line_id.type_id.id == self.env.ref('connector_backend_home.ftp').id:
            record = self._callwrite_ftp(filename, content)
        if self.backend_record.connector_id.line_id.type_id.id == self.env.ref('connector_backend_home.local').id:
            record = self._callwrite_local(filename, content)

        return record

    def set_stock_level(self, param):
        return self._call('stock/quantities', param, meth="POST")


@magentoextend
class ProductBatchImporterV2(DelayedBatchImporterV2):
    """ Import the magentoextendCommerce Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magentoextend2.product.product']

    def _import_record(self, magentoextend_id, priority=None):
        """ Delay a job for the import """
        import_record_product_v2.delay(self.session,
                            self.model._name,
                            self.backend_record.id,
                            magentoextend_id,
                            priority=priority)

    def run(self, filters=None):
        """ Run the synchronization """
        #
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        record_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
        )
        _logger.info('search for magentoextend Products %s returned %s',
                     filters, record_ids)
        if record_ids:
            self._import_record(record_ids, 30)


ProductBatchImporterV2 = ProductBatchImporterV2


@magentoextend
class ProductProductImporterV2(magentoextendImporterV2):
    _model_name = ['magentoextend2.product.product']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""

    def _get_magentoextend_data(self):
        filters = {}
        filters['searchCriteria[filter_groups][0][filters][0][field]'] = 'entity_id'
        filters['searchCriteria[filter_groups][0][filters][0][condition_type]'] = 'eq'
        filters['searchCriteria[filter_groups][0][filters][0][value]'] = self.magentoextend_id
        items = self.backend_adapter.read(filters)
        if items.get("items"):
            return items.get("items")[0]
        return False

    def _create(self, data):
        openerp_binding = super(ProductProductImporterV2, self)._create(data)
        return openerp_binding

    def _after_import(self, binding, sku):
        """ Hook called at the end of the import """
        image_importer = self.unit_for(ProductImageImporterV2)
        image_importer.run(self.magentoextend_id, binding.id, sku)
        return

    def run(self, magentoextend_id, force=False):
        """ Run the synchronization

        :param magentoextend_id: identifier of the record on magentoextendCommerce
        """
        self.magentoextend_id = magentoextend_id
        try:
            self.magentoextend_record = self._get_magentoextend_data()
        except IDMissingInBackend:
            return _('Record does no longer exist in magentoextendCommerce')

        skip = self._must_skip()
        if skip:
            return skip

        binding = self._get_binding()
        if not binding:
            openerp_id = self.env['product.product'].search([('name', '=',
                                                              self.magentoextend_record.get("name")),
                                                             ('default_code', '=',
                                                              self.magentoextend_record.get("sku")),
                                                             ('owner_id', '=',
                                                              self.backend_record.connector_id.home_id.partner_id.id)])
            if openerp_id:
                self.env['magentoextend2.product.product'].create({
                    'magentoextend_id': self.magentoextend_record.get("id"),
                    'backend_home_id': self.backend_record.connector_id.home_id.id,
                    'backend_id': self.backend_record.id,
                    'updated_at': self.magentoextend_record.get('updated_at'),
                    'created_at': self.magentoextend_record.get('created_at'),
                    'openerp_id': openerp_id[0].id
                })
                binding = self._get_binding()

        if not force and self._is_uptodate(binding):
            return _('Already up-to-date.')
        self._before_import()

        # import the missing linked resources
        self._import_dependencies()

        map_record = self._map_data()

        if binding:
            record = self._update_data(map_record)
            self._update(binding, record)
        else:

            record = self._create_data(map_record)
            record["backend_id"] = self.backend_record.id
            binding = self._create(record)
        self.binder.bind(self.magentoextend_id, binding)

        self._after_import(binding, self.magentoextend_record.get("sku"))


ProductProductImporterV2 = ProductProductImporterV2


@magentoextend
class ProductImageImporterV2(Importer):
    """ Import images for a record.

    Usually called from importers, in ``_after_import``.
    For instance from the products importer.
    """
    _model_name = ['magentoextend2.product.product',
                   ]

    def _get_images(self, sku, storeview_id=None):
        return self.backend_adapter.get_images(sku)

    def _sort_images(self, images):
        """ Returns a list of images sorted by their priority.
        An image with the 'image' type is the the primary one.
        The other images are sorted by their position.

        The returned list is reversed, the items at the end
        of the list have the higher priority.
        """
        if not images:
            return {}

        # place the images where the type is 'image' first then
        # sort them by the reverse priority (last item of the list has
        # the the higher priority)

        def priority(image):
            try:
                primary = 'image' in image['types']
                position = int(image['position'])
            except ValueError:
                position = sys.maxint
            return (primary, -position)

        return sorted(images, key=priority)

    def _get_binary_image(self, image_data):
        url = image_data['file'].encode('utf8')
        try:
            param = self.env[self.backend_record.connector_id.line_id.type_id.model_name].search(
                [('line_id', '=', self.backend_record.connector_id.line_id.id)])
            request = urllib2.Request(param.url.replace("index.php/rest/V1", "media/catalog/product")+url)
            if param.use_http:
                base64string = base64.b64encode(
                    '%s:%s' % (param.http_user,
                               param.http_pwd))
                request.add_header("Authorization", "Basic %s" % base64string)
            binary = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            if err.code == 404:
                # the image is just missing, we skip it
                return
            else:
                # we don't know why we couldn't download the image
                # so we propagate the error, the import will fail
                # and we have to check why it couldn't be accessed
                raise
        else:
            return binary.read()

    def run(self, magentoextend_id, binding_id, sku):
        self.magentoextend_id = magentoextend_id
        images = self._get_images(sku)
        images = self._sort_images(images)
        binary = None
        while not binary and images:
            binary = self._get_binary_image(images.pop())
        if not binary:
            return
        model = self.model.with_context(connector_no_export=True)
        binding = model.browse(binding_id)

        try:
            binding.write({'image': base64.b64encode(binary)})
        except IOError:
            #fichier corrompu
            pass


@magentoextend
class ProductProductImportMapper(ImportMapper):
    _model_name = 'magentoextend2.product.product'

    direct = [('name', 'name'),
              ('sku', 'default_code'),
              ('weight', 'weight'),
              ('type_id', 'product_type'),
              ('created_at', 'created_at'),
              ('updated_at', 'updated_at'),
              ]

    @mapping
    def description(self, record):
        if record.get("custom_attributes"):
            for item in record.get("custom_attributes"):
                if item["attribute_code"] == "description":
                    return {'description': item["value"]}
        return {'description': False}

    @mapping
    def short_description(self, record):
        if record.get("custom_attributes"):
            for item in record.get("custom_attributes"):
                if item["attribute_code"] == "short_description":
                    return {'description_sale': item["value"]}
        return {'description_sale': False}

    @mapping
    def cost(self, record):
        if record.get("custom_attributes"):
            for item in record.get("custom_attributes"):
                if item["attribute_code"] == "cost":
                    return {'cost': item["value"]}
        return {'cost': 0}

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
    def type(self, record):
        if record['type_id'] == 'simple':
            return {'type': 'product'}
        return

    @mapping
    def magentoextend_id(self, record):
        return {'magentoextend_id': record['id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def owner_id(self, record):
        return {'owner_id': self.backend_record.connector_id.home_id.partner_id.id}


@magentoextend
class StockLevelExporter(Exporter):
    _model_name = 'magentoextend2.product.product'

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
          magentoextend_id,
          default_code,
          sum(qty) qty
          from (
          SELECT
               sq.product_id,
               mpp.magentoextend_id,
               pp.default_code,
               sum(sq.qty) qty
             FROM
               stock_quant sq
               LEFT JOIN magentoextend_product_product mpp ON mpp.openerp_id = sq.product_id
               LEFT JOIN product_product pp ON mpp.openerp_id = pp.id
               LEFT JOIN top_parent tp ON tp.loc_id = sq.location_id
               LEFT JOIN stock_location sl ON sl.id = tp.top_parent_id
             where mpp.backend_home_id = %s and sl.id =%s
             GROUP BY
               sq.product_id,
               mpp.magentoextend_id,
               pp.default_code

            union ALL

            SELECT
               pp.id,
               mpp.magentoextend_id,
               pp.default_code,
               0 qty
            FROM
               magentoextend_product_product mpp
               LEFT JOIN product_product pp ON mpp.openerp_id = pp.id
            where mpp.backend_home_id = %s) rqx
            group by
            product_id,
            magentoextend_id,
            default_code
                    """, (self.backend_record.connector_id.home_id.id,
                          self.backend_record.connector_id.home_id.warehouse_id.lot_stock_id.id,
                          self.backend_record.connector_id.home_id.id
                          ))

        log = ""

        export = False
        param = {"stockQuantities": {}}

        for product in self.env.cr.dictfetchall():
            export = True
            qty = int(product['qty'])
            log += "\n%s : %s\n" % (product['default_code'], str(qty))
            if float_compare(product['qty'], 0, 1) <= 0:
                qty = int(0)
            if product['magentoextend_id']:
                param["stockQuantities"][product['magentoextend_id']] = qty

        if export:
            self.backend_adapter.set_stock_level(param)

        return log


@job(default_channel='root.magentoextend_pull_product_product')
def product_import_v2_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of product modified on magentoextend """
    if filters is None:
        filters = {}
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(ProductBatchImporterV2)
    importer.run(filters=filters)


@job(default_channel='root.magentoextend_push_product_level')
def product_export_stock_level_v2_batch(session, model_name, backend_id, filters=None):
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(StockLevelExporter)
    importer.run()


@job(default_channel='root.magentoextend_pull_product_product')
@related_action(action=link)
def import_record_product_v2(session, model_name, backend_id, magentoextend_ids, force=False):
    """ Import a record from magentoextend """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(ProductProductImporterV2)
    log = ""
    for id in magentoextend_ids:
        print id
        log = log + '\n' + str(id) + '\n' + '----------' + '\n'
        resp = str(importer.run(id, force=force))
        log = log + resp

    return log

