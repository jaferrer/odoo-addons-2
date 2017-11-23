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

import logging
import xmlrpclib

from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.mapper import (mapping,
                                                  ImportMapper
                                                  )

from openerp import models, fields, api
from ..backend import magentoextend
from ..connector import get_environment
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.import_synchronizer import (DelayedBatchImporter, magentoextendImporter)

_logger = logging.getLogger(__name__)


class magentoextend_sale_order_status(models.Model):
    _name = 'magentoextend.sale.order.status'
    _description = 'magentoextendCommerce Sale Order Status'

    name = fields.Char('Name')
    desc = fields.Text('Description')


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    status_id = fields.Many2one('magentoextend.sale.order.status',
                                'magentoextendCommerce Order Status')


class magentoextendSaleOrder(models.Model):
    _name = 'magentoextend.sale.order'
    _inherit = 'magentoextend.binding'
    _inherits = {'sale.order': 'openerp_id'}
    _description = 'magentoextend Sale Order'

    _rec_name = 'name'

    status_id = fields.Many2one('magentoextend.sale.order.status',
                                'magentoextendCommerce Order Status')

    openerp_id = fields.Many2one(comodel_name='sale.order',
                                 string='Sale Order',
                                 required=True,
                                 ondelete='cascade')
    magentoextend_order_line_ids = fields.One2many(
        comodel_name='magentoextend.sale.order.line',
        inverse_name='magentoextend_order_id',
        string='magentoextend Order Lines'
    )
    backend_id = fields.Many2one(
        comodel_name='wc.backend',
        string='magentoextend Backend',
        store=True,
        readonly=False,
        required=True,
    )


class magentoextendSaleOrderLine(models.Model):
    _name = 'magentoextend.sale.order.line'
    _inherits = {'sale.order.line': 'openerp_id'}

    magentoextend_order_id = fields.Many2one(comodel_name='magentoextend.sale.order',
                                             string='magentoextend Sale Order',
                                             required=True,
                                             ondelete='cascade',
                                             select=True)

    openerp_id = fields.Many2one(comodel_name='sale.order.line',
                                 string='Sale Order Line',
                                 required=True,
                                 ondelete='cascade')

    backend_id = fields.Many2one(
        related='magentoextend_order_id.backend_id',
        string='magentoextend Backend',
        readonly=True,
        store=True,
        required=False,
    )

    @api.model
    def create(self, vals):
        magentoextend_order_id = vals['magentoextend_order_id']
        binding = self.env['magentoextend.sale.order'].browse(magentoextend_order_id)
        vals['order_id'] = binding.openerp_id.id
        binding = super(magentoextendSaleOrderLine, self).create(vals)
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    magentoextend_bind_ids = fields.One2many(
        comodel_name='magentoextend.sale.order.line',
        inverse_name='openerp_id',
        string="magentoextendCommerce Bindings",
    )


@magentoextend
class SaleOrderLineImportMapper(ImportMapper):
    _model_name = 'magentoextend.sale.order.line'

    direct = [('quantity', 'product_uom_qty'),
              ('quantity', 'product_uos_qty'),
              ('name', 'name'),
              ('price', 'price_unit')
              ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for('magentoextend.product.product')
        product_id = binder.to_openerp(record['product_id'], unwrap=True)
        assert product_id is not None, (
            "product_id %s should have been imported in "
            "SaleOrderImporter._import_dependencies" % record['product_id'])
        return {'product_id': product_id}


@magentoextend
class SaleOrderAdapter(GenericAdapter):
    _model_name = 'magentoextend.sale.order'
    _magentoextend_model = 'orders'

    def _call(self, method, arguments):
        try:
            return super(SaleOrderAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the magentoextend API
            # when the customer does not exist
            if err.faultCode == 102:
                raise IDMissingInBackend
            else:
                raise

    def search(self, filters=None, from_date=None, to_date=None):
        """ Search records according to some criteria and return a
        list of ids

        :rtype: list
        """
        if filters is None:
            filters = {}
        magentoextend_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'
        dt_fmt = magentoextend_DATETIME_FORMAT
        if from_date is not None:
            # updated_at include the created records
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)

        return self._call('orders/list',
                          [filters] if filters else [{}])


@magentoextend
class SaleOrderBatchImporter(DelayedBatchImporter):
    """ Import the magentoextendCommerce Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magentoextend.sale.order']

    def _import_record(self, magentoextend_id, priority=None):
        """ Delay a job for the import """
        super(SaleOrderBatchImporter, self)._import_record(
            magentoextend_id, priority=priority)

    def update_existing_order(self, magentoextend_sale_order, record_id):
        """ Enter Your logic for Existing Sale Order """
        return True

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
        order_ids = []
        for record_id in record_ids:
            magentoextend_sale_order = self.env['magentoextend.sale.order'].search(
                [('magentoextend_id', '=', record_id)])
            if magentoextend_sale_order:
                self.update_existing_order(magentoextend_sale_order[0], record_id)
            else:
                order_ids.append(record_id)
        _logger.info('search for magentoextend partners %s returned %s',
                     filters, record_ids)
        for record_id in order_ids:
            self._import_record(record_id, 50)


SaleOrderBatchImporter = SaleOrderBatchImporter


#


@magentoextend
class SaleOrderImporter(magentoextendImporter):
    _model_name = ['magentoextend.sale.order']

    def _import_addresses(self):
        record = self.magentoextend_record
        record = record['order']
        self._import_dependency(record['customer_id'],
                                'magentoextend.res.partner')

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        record = self.magentoextend_record

        self._import_addresses()
        record = record['items']
        for line in record:
            _logger.debug('line: %s', line)
            if 'product_id' in line:
                self._import_dependency(line['product_id'],
                                        'magentoextend.product.product')

    def _clean_magentoextend_items(self, resource):
        """
        Method that clean the sale order line given by magentoextendCommerce before
        importing it

        This method has to stay here because it allow to customize the
        behavior of the sale order.

        """
        child_items = {}  # key is the parent item id
        top_items = []

        # Group the childs with their parent
        for item in resource['order']['line_items']:
            if item.get('parent_item_id'):
                child_items.setdefault(item['parent_item_id'], []).append(item)
            else:
                top_items.append(item)

        all_items = []
        for top_item in top_items:
            all_items.append(top_item)
        resource['items'] = all_items
        return resource

    def _create(self, data):
        openerp_binding = super(SaleOrderImporter, self)._create(data)
        return openerp_binding

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def _get_magentoextend_data(self):
        """ Return the raw magentoextendCommerce data for ``self.magentoextend_id`` """
        record = super(SaleOrderImporter, self)._get_magentoextend_data()
        # sometimes we need to clean magentoextend items (ex : configurable
        # product in a sale)
        record = self._clean_magentoextend_items(record)
        return record


SaleOrderImport = SaleOrderImporter


@magentoextend
class SaleOrderImportMapper(ImportMapper):
    _model_name = 'magentoextend.sale.order'

    children = [('items', 'magentoextend_order_line_ids', 'magentoextend.sale.order.line'),
                ]

    @mapping
    def status(self, record):
        if record['order']:
            rec = record['order']
            if rec['status']:
                status_id = self.env['magentoextend.sale.order.status'].search(
                    [('name', '=', rec['status'])])
                if status_id:
                    return {'status_id': status_id[0].id}
                else:
                    status_id = self.env['magentoextend.sale.order.status'].create({
                        'name': rec['status']
                    })
                    return {'status_id': status_id.id}
            else:
                return {'status_id': False}

    @mapping
    def customer_id(self, record):
        if record['order']:
            rec = record['order']
            binder = self.binder_for('magentoextend.res.partner')
            if rec['customer_id']:
                partner_id = binder.to_openerp(rec['customer_id'],
                                               unwrap=True) or False
                #               customer_id = str(rec['customer_id'])
                assert partner_id, ("Please Check Customer Role \
                                    in magentoextendCommerce")
                result = {'partner_id': partner_id}
                onchange_val = self.env['sale.order'].onchange_partner_id(
                    partner_id)
                result.update(onchange_val['value'])
            else:
                customer = rec['customer']['billing_address']
                country_id = False
                state_id = False
                if customer['country']:
                    country_id = self.env['res.country'].search(
                        [('code', '=', customer['country'])])
                    if country_id:
                        country_id = country_id.id
                if customer['state']:
                    state_id = self.env['res.country.state'].search(
                        [('code', '=', customer['state'])])
                    if state_id:
                        state_id = state_id.id
                name = customer['first_name'] + ' ' + customer['last_name']
                partner_dict = {
                    'name': name,
                    'city': customer['city'],
                    'phone': customer['phone'],
                    'zip': customer['postcode'],
                    'state_id': state_id,
                    'country_id': country_id
                }
                partner_id = self.env['res.partner'].create(partner_dict)
                partner_dict.update({
                    'backend_id': self.backend_record.id,
                    'openerp_id': partner_id.id,
                })
                #                 magentoextend_partner_id = self.env['magentoextend.res.partner'].create(
                #                     partner_dict)
                result = {'partner_id': partner_id.id}
                onchange_val = self.env['sale.order'].onchange_partner_id(
                    partner_id.id)
                result.update(onchange_val['value'])
            return result

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}


@job(default_channel='root.magentoextend')
def sale_order_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Sale Order modified on magentoextend """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(SaleOrderBatchImporter)
    importer.run(filters=filters)