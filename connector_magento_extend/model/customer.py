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
from collections import namedtuple

from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector.exception import IDMissingInBackend
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.unit.backend_adapter import BackendAdapter
from openerp.addons.connector.unit.mapper import (mapping,
                                                  only_create,
                                                  ImportMapper
                                                  )

from openerp import models, fields
from ..backend import magentoextend
from ..connector import get_environment
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.import_synchronizer import (DelayedBatchImporter, magentoextendImporter)
from ..unit.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


class magentoextendResPartner(models.Model):
    _name = 'magentoextend.res.partner'
    _inherit = 'magentoextend.binding'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'magentoextend res partner'

    _rec_name = 'name'

    openerp_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner',
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

    updated_at = fields.Datetime(string='Updated At (on Magento)',
                                 readonly=True)

    created_at = fields.Datetime(string='Created At (on Magento)',
                                 readonly=True)


class MagentoAddress(models.Model):
    _name = 'magentoextend.address'
    _inherit = 'magentoextend.binding'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'magentoextend Address'

    _rec_name = 'backend_id'

    openerp_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner',
                                 required=True,
                                 ondelete='cascade')
    created_at = fields.Datetime(string='Created At (on Magento)',
                                 readonly=True)
    updated_at = fields.Datetime(string='Updated At (on Magento)',
                                 readonly=True)
    is_default_billing = fields.Boolean(string='Default Invoice')
    is_default_shipping = fields.Boolean(string='Default Shipping')
    magento_partner_id = fields.Many2one(comodel_name='magentoextend.res.partner',
                                         string='Magento Partner',
                                         required=True,
                                         ondelete='cascade')
    backend_id = fields.Many2one(
        related='magento_partner_id.backend_id',
        comodel_name='magentoextend.backend',
        string='Magento Backend',
        store=True,
        readonly=True,
        # override 'magento.binding', can't be INSERTed if True:
        required=False,
    )

    backend_home_id = fields.Many2one(
        related='backend_id.connector_id.home_id',
        comodel_name='backend.home',
        string='Backend Home',
        store=True,
        required=False,
        ondelete='restrict',
    )

    is_magento_order_address = fields.Boolean(
        string='Address from a Magento Order',
    )

    _sql_constraints = [
        ('openerp_uniq', 'unique(backend_id, openerp_id)',
         'A partner address can only have one binding by backend.'),
    ]


@magentoextend
class CustomerAdapter(GenericAdapter):
    _model_name = 'magentoextend.res.partner'
    _magentoextend_model = 'customer'

    def _call(self, method, arguments):
        try:
            return super(CustomerAdapter, self)._call(method, arguments)
        except xmlrpclib.Fault as err:
            # this is the error in the magentoextendCommerce API
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
        MAGENTO_DATETIME_FORMAT = '%Y/%m/%d %H:%M:%S'
        dt_fmt = MAGENTO_DATETIME_FORMAT
        if from_date is not None:
            # updated_at include the created records
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = from_date.strftime(dt_fmt)
        if to_date is not None:
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(dt_fmt)
        # the search method is on ol_customer instead of customer
        return {
            'customers': [{'id': int(row['customer_id'])} for row in self._call('customer.list',
                                                                                [filters] if filters else [{}])]
        }


@magentoextend
class CustomerBatchImporter(DelayedBatchImporter):
    """ Import the magentoextendCommerce Partners.

    For every partner in the list, a delayed job is created.
    """
    _model_name = ['magentoextend.res.partner']

    def _import_record(self, magentoextend_id, priority=None):
        """ Delay a job for the import """
        super(CustomerBatchImporter, self)._import_record(
            magentoextend_id, priority=priority)

    def run(self, filters=None):
        """ Run the synchronization """
        from_date = filters.pop('from_date', None)
        to_date = filters.pop('to_date', None)
        record_ids = self.backend_adapter.search(
            filters,
            from_date=from_date,
            to_date=to_date,
        )
        record_ids = self.env['magentoextend.backend'].get_customer_ids(record_ids)
        _logger.info('search for magentoextend partners %s returned %s',
                     filters, record_ids)
        if record_ids:
            self._import_record(record_ids, 40)


CustomerBatchImporter = CustomerBatchImporter  # deprecated


@magentoextend
class CustomerImporter(magentoextendImporter):
    _model_name = ['magentoextend.res.partner']

    def _import_dependencies(self):
        """ Import the dependencies for the record"""
        return

    def _create(self, data):
        openerp_binding = super(CustomerImporter, self)._create(data)
        return openerp_binding

    def _after_import(self, binding):
        """ Import the addresses """
        book = self.unit_for(PartnerAddressBook, model='magentoextend.address')
        book.import_addresses(self.magentoextend_id, binding.id)


CustomerImport = CustomerImporter

AddressInfos = namedtuple('AddressInfos', ['magento_record',
                                           'partner_binding_id',
                                           'merge'])


@magentoextend
class PartnerAddressBook(ConnectorUnit):
    """ Import all addresses from the address book of a customer.

        This class is responsible to define which addresses should
        be imported and how (merge with the partner or not...).
        Then, it delegate the import to the appropriate importer.

        This is really intricate. The datamodel are different between
        Magento and OpenERP and we have many uses cases to cover.

        The first thing is that:
            - we do not import companies and individuals the same manner
            - we do not know if an account is a company -> we assume that
              if we found something in the company field of the billing
              address, the whole account is a company.

        Differences:
            - Individuals: we merge the billing address with the partner,
              so we'll end with 1 entity if the customer has 1 address
            - Companies: we never merge the addresses with the partner,
              but we use the company name of the billing address as name
              of the partner. We also copy the address informations from
              the billing address as default values.

        More information on:
        https://bugs.launchpad.net/openerp-connector/+bug/1193281
    """
    _model_name = 'magentoextend.address'

    def import_addresses(self, magento_partner_id, partner_binding_id):
        addresses = self._get_address_infos(magento_partner_id,
                                            partner_binding_id)
        for address_id, infos in addresses:
            importer = self.unit_for(magentoextendImporter)
            importer.run(address_id, address_infos=infos)

    def _get_address_infos(self, magento_partner_id, partner_binding_id):
        adapter = self.unit_for(BackendAdapter)
        mag_address_ids = adapter.search(magento_partner_id)
        if not mag_address_ids:
            return
        for address_id in mag_address_ids:
            magento_record = adapter.read(address_id)

            # defines if the billing address is merged with the partner
            # or imported as a standalone contact
            merge = False
            if magento_record.get('is_default_billing'):
                binding_model = self.env['magentoextend.res.partner']
                partner_binding = binding_model.browse(partner_binding_id)
                # for B2C individual customers, merge with the main
                # partner
                merge = True
                # in the case if the billing address no longer
                # has a company, reset the flag
                partner_binding.write({'consider_as_company': False})
            address_infos = AddressInfos(magento_record=magento_record,
                                         partner_binding_id=partner_binding_id,
                                         merge=merge)
            yield address_id, address_infos


class BaseAddressImportMapper(ImportMapper):
    """ Defines the base mappings for the imports
    in ``res.partner`` (state, country, ...)
    """
    direct = [('postcode', 'zip'),
              ('city', 'city'),
              ('telephone', 'phone'),
              ('fax', 'fax'),
              ]

    @mapping
    def state(self, record):
        if not record.get('region'):
            return
        state = self.env['res.country.state'].search(
            [('name', '=ilike', record['region'])],
            limit=1,
        )
        if state:
            return {'state_id': state.id}

    @mapping
    def country(self, record):
        if not record.get('country_id'):
            return
        country = self.env['res.country'].search(
            [('code', '=', record['country_id'])],
            limit=1,
        )
        if country:
            return {'country_id': country.id}

    @mapping
    def street(self, record):
        value = record['street']
        lines = [line.strip() for line in value.split('\n') if line.strip()]
        if len(lines) == 1:
            result = {'street': lines[0], 'street2': False}
        elif len(lines) >= 2:
            result = {'street': lines[0], 'street2': u' - '.join(lines[1:])}
        else:
            result = {}
        return result

    @mapping
    def title(self, record):
        prefix = record['prefix']
        if not prefix:
            return
        title = self.env['res.partner.title'].search(
            [('shortcut', '=ilike', prefix)],
            limit=1
        )
        if not title:
            title = self.env['res.partner.title'].create(
                {'shortcut': prefix,
                 'name': prefix,
                 }
            )
        return {'title': title.id}

    @only_create
    @mapping
    def company_id(self, record):
        return {'company_id': False}


@magentoextend
class AddressAdapter(GenericAdapter):
    _model_name = 'magentoextend.address'
    _magentoextend_model = 'customer_address'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return [int(row['customer_address_id']) for row
                in self._call('%s.list' % self._magentoextend_model,
                              [filters] if filters else [{}])]

    def create(self, customer_id, data):
        """ Create a record on the external system """
        return self._call('%s.create' % self._magento_model,
                          [customer_id, data])


@magentoextend
class AddressImporter(magentoextendImporter):
    _model_name = ['magentoextend.address']

    def run(self, magento_id, address_infos=None, force=False):
        """ Run the synchronization """
        if address_infos is None:
            # only possible for updates
            self.address_infos = AddressInfos(None, None, None)
        else:
            self.address_infos = address_infos
        return super(AddressImporter, self).run(magento_id, force=force)

    def _get_magento_data(self):
        """ Return the raw Magento data for ``self.magento_id`` """
        # we already read the data from the Partner Importer
        if self.address_infos.magento_record:
            return self.address_infos.magento_record
        else:
            return super(AddressImporter, self)._get_magento_data()

    def _define_partner_relationship(self, data):
        """ Link address with partner or parent company. """
        partner_binding_id = self.address_infos.partner_binding_id
        assert partner_binding_id, ("AdressInfos are required for creation of "
                                    "a new address.")
        binder = self.binder_for('magentoextend.res.partner')
        partner = binder.unwrap_binding(partner_binding_id, browse=True)
        if self.address_infos.merge:
            # it won't be imported as an independent address,
            # but will be linked with the main res.partner
            data['openerp_id'] = partner.id
            data['type'] = 'contact'
        else:
            data['parent_id'] = partner.id
            data['lang'] = partner.lang
        data['magento_partner_id'] = self.address_infos.partner_binding_id
        return data

    def _create(self, data):
        data = self._define_partner_relationship(data)
        return super(AddressImporter, self)._create(data)


AddressImport = AddressImporter  # deprecated


@magentoextend
class AddressImportMapper(BaseAddressImportMapper):
    _model_name = 'magentoextend.address'

    # TODO fields not mapped:
    #   "suffix"=>"a",
    #   "vat_id"=>"12334",

    direct = BaseAddressImportMapper.direct + [
        ('created_at', 'created_at'),
        ('updated_at', 'updated_at'),
        ('is_default_billing', 'is_default_billing'),
        ('is_default_shipping', 'is_default_shipping'),
    ]

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in (record['firstname'],
                                   record.get('middlename'),
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @mapping
    def use_parent_address(self, record):
        return {'use_parent_address': False}

    @mapping
    def type(self, record):
        if record.get('is_default_billing'):
            address_type = 'invoice'
        elif record.get('is_default_shipping'):
            address_type = 'delivery'
        else:
            address_type = 'contact'
        return {'type': address_type}


@magentoextend
class CustomerImportMapper(ImportMapper):
    _model_name = 'magentoextend.res.partner'

    direct = [
        ('email', 'email'),
        ('dob', 'birthdate'),
        (normalize_datetime('created_at'), 'created_at'),
        (normalize_datetime('updated_at'), 'updated_at'),
    ]

    @only_create
    @mapping
    def is_company(self, record):
        # partners are companies so we can bind
        # addresses on them
        return {'company_type': 'company'}

    @mapping
    def names(self, record):
        # TODO create a glue module for base_surname
        parts = [part for part in (record['firstname'],
                                   record['middlename'],
                                   record['lastname']) if part]
        return {'name': ' '.join(parts)}

    @only_create
    @mapping
    def company_id(self, record):
        return {'company_id': False}

    @only_create
    @mapping
    def customer(self, record):
        return {'customer': True}

    @mapping
    def type(self, record):
        return {'type': 'contact'}

    @only_create
    @mapping
    def openerp_id(self, record):
        """ Will bind the customer on a existing partner
        with the same email """
        partner = self.env['res.partner'].search(
            [('email', '=', record['email']),
             ('customer', '=', True),
             '|',
             ('is_company', '=', True),
             ('parent_id', '=', False)],
            limit=1,
        )
        if partner:
            return {'openerp_id': partner.id}

    @mapping
    def magentoextend_id(self, record):
        return {'magentoextend_id': record['customer_id']}

    @only_create
    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @only_create
    @mapping
    def owner_id(self, record):
        return {'owner_id': self.backend_record.connector_id.home_id.partner_id.id}


@job(default_channel='root.magentoextend')
def customer_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Customer """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(CustomerBatchImporter)
    importer.run(filters=filters)


class ResPartnerBackend(models.Model):
    _inherit = 'res.partner'

    owner_id = fields.Many2one('res.partner', string=u"Owner")
