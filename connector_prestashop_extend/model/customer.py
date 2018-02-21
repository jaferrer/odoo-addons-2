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
from ..unit.mapper import backend_to_m2o

from openerp import models, fields, api
from ..backend import prestashopextend
from ..connector import get_environment
from ..unit.backend_adapter import (GenericAdapter)
from ..unit.importer import (DelayedBatchImporter, prestashopextendImporter, import_batch)
from ..unit.direct_binder import DirectBinder

_logger = logging.getLogger(__name__)


class customerResPartner(models.Model):
    _name = 'res.partner.custom.field'

    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner',
                                 required=True)

    field = fields.Char(string='field odoo')

    field_mapping = fields.Char(string='field source')


class customerResPartner(models.Model):
    _inherit = 'res.partner'

    final_customer = fields.Boolean(string='Final Customer')
    customer_point = fields.Float(string='Customer Point')
    address_company_name = fields.Char(string="Nom de la boutique point relais")
    id_relais = fields.Char(string="Id point relais")
    custom_field_mapping = fields.One2many('res.partner.custom.field', 'partner_id', string=u"'Mapping Custom Field'")


class magentoextendResPartner(models.Model):
    _name = 'prestashopextend.res.partner'
    _inherit = 'prestashopextend.binding.odoo'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'prestashopextend res partner'

    _rec_name = 'name'

    openerp_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner',
                                 required=True,
                                 ondelete='cascade')

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

    date_upd = fields.Datetime(string='Updated At (on Prestashop)',
                                 readonly=True)

    date_add = fields.Datetime(string='Created At (on Prestashop)',
                                 readonly=True)

    @api.model
    def create(self, vals):
        vals['final_customer'] = True
        binding = super(magentoextendResPartner, self).create(vals)
        return binding


class MagentoAddress(models.Model):
    _name = 'prestashopextend.address'
    _inherit = 'prestashopextend.binding.odoo'
    _inherits = {'res.partner': 'openerp_id'}
    _description = 'prestashopextend Address'

    _rec_name = 'backend_id'

    openerp_id = fields.Many2one(comodel_name='res.partner',
                                 string='Partner',
                                 required=True,
                                 ondelete='cascade')
    date_add = fields.Datetime(string='Created At (on Magento)',
                               readonly=True)
    date_upd = fields.Datetime(string='Updated At (on Magento)',
                               readonly=True)

    prestashop_partner_id = fields.Many2one(comodel_name='prestashopextend.res.partner',
                                            string='prestashop Partner',
                                            required=True,
                                            ondelete='cascade')

    backend_id = fields.Many2one(
        related='prestashop_partner_id.backend_id',
        comodel_name='prestashopextend.backend',
        string='prestashopextend Backend',
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

    _sql_constraints = [
        ('openerp_uniq', 'unique(backend_id, openerp_id)',
         'A partner address can only have one binding by backend.'),
    ]

    @api.model
    def create(self, vals):
        vals['final_customer'] = True
        binding = super(MagentoAddress, self).create(vals)
        return binding


@prestashopextend
class PartnerAdapter(GenericAdapter):
    _model_name = 'prestashopextend.res.partner'
    _prestashopextend_model = 'customers'


@prestashopextend
class PartnerAddressAdapter(GenericAdapter):
    _model_name = 'prestashopextend.address'
    _prestashopextend_model = 'addresses'


@prestashopextend
class PartnerImportMapper(ImportMapper):
    _model_name = 'prestashopextend.res.partner'

    direct = [
        ('date_add', 'date_add'),
        ('date_upd', 'date_upd'),
        ('email', 'email'),
        ('note', 'comment'),
    ]

    @mapping
    def prestashopextend_id(self, record):
        return {'prestashopextend_id': record['id']}

    @mapping
    def name(self, record):
        name = ""
        if record['firstname']:
            name += record['firstname']
        if record['lastname']:
            if len(name) != 0:
                name += " "
            name += record['lastname']
        return {'name': name}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def customer(self, record):
        return {'customer': False}

    @mapping
    def is_company(self, record):
        # This is sad because we _have_ to have a company partner if we want to
        # store multiple adresses... but... well... we have customers who want
        # to be billed at home and be delivered at work... (...)...
        return {'is_company': True}

    @mapping
    def company_id(self, record):
        return {'company_id': False}

    @only_create
    @mapping
    def owner_id(self, record):
        return {'owner_id': self.backend_record.connector_id.home_id.partner_id.id}


@prestashopextend
class ResPartnerRecordImport(prestashopextendImporter):
    _model_name = 'prestashopextend.res.partner'

    def _after_import(self, erp_id):
        binder = self.binder_for(self._model_name)
        ps_id = binder.to_backend(erp_id)
        import_batch.delay(
            self.session,
            'prestashopextend.address',
            self.backend_record.id,
            filters={'filter[id_customer]': '%s' % (ps_id)},
            priority=10,
        )


@prestashopextend
class PartnerBatchImporter(DelayedBatchImporter):
    _model_name = 'prestashopextend.res.partner'


@prestashopextend
class AddressImportMapper(ImportMapper):
    _model_name = 'prestashopextend.address'

    direct = [
        ('address1', 'street'),
        ('address2', 'street2'),
        ('city', 'city'),
        ('other', 'comment'),
        ('phone', 'phone'),
        ('phone_mobile', 'mobile'),
        ('postcode', 'zip'),
        ('date_add', 'date_add'),
        ('date_upd', 'date_upd'),
        ('company', 'address_company_name'),
        (backend_to_m2o('id_customer'), 'prestashop_partner_id'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def partner_type(self, record):
        return {'type': 'delivery'}

    @mapping
    def parent_id(self, record):
        parent = self.binder_for('prestashopextend.res.partner').to_openerp(
            record['id_customer'], unwrap=True, browse=True)
        return {'parent_id': parent.id}

    @mapping
    def name(self, record):
        name = ""
        if record['firstname']:
            name += record['firstname']
        if record['lastname']:
            if name:
                name += " "
            name += record['lastname']
        return {'name': name}

    @mapping
    def customer(self, record):
        return {'customer': False}

    @mapping
    def country(self, record):
        if record.get('id_country'):
            binder = self.binder_for('prestashopextend.res.country')
            erp_country = binder.to_openerp(record['id_country'], unwrap=True)
            return {'country_id': erp_country}
        return {}

    @mapping
    def company_id(self, record):
        return {'company_id': False}

    @mapping
    def prestashopextend_id(self, record):
        return {'prestashopextend_id': record['id']}


@prestashopextend
class AddressImporter(prestashopextendImporter):
    _model_name = 'prestashopextend.address'

    def _import_dependencies(self):
        record = self.prestashopextend_record
        binder = self.binder_for('prestashopextend.res.country').to_openerp(record['id_country'], unwrap=True)
        if not binder:
            self._import_dependency(
                record['id_country'], 'prestashopextend.res.country'
            )


@prestashopextend
class AddressBatchImporter(DelayedBatchImporter):
    _model_name = 'prestashopextend.address'


class PrestashopResCountry(models.Model):
    _name = 'prestashopextend.res.country'
    _inherit = 'prestashopextend.binding.odoo'
    _inherits = {'res.country': 'openerp_id'}

    openerp_id = fields.Many2one(comodel_name='res.country',
                                 string='Country',
                                 required=True,
                                 ondelete='cascade')

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

    @api.model
    def create(self, vals):
        if vals.get("openerp_id"):
            binding = super(PrestashopResCountry, self).create(vals)
            return binding
        return False


@prestashopextend
class ResCountryAdapter(GenericAdapter):
    _model_name = 'prestashopextend.res.country'
    _prestashopextend_model = 'countries'


@prestashopextend
class CountryImportMapper(ImportMapper):
    _model_name = 'prestashopextend.res.country'

    def _compare_function(self, ps_val, erp_val):
        if (
            erp_val and
            ps_val and
            len(erp_val) >= 2 and
            len(ps_val) >= 2 and
            erp_val[0:2].lower() == ps_val[0:2].lower()
        ):
            return True
        return False

    @mapping
    def prestashopextend_id(self, record):
        return {'prestashopextend_id': record['id']}

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def openerp_id(self, record):
        countrys = self.env["res.country"].search([])
        for rc in countrys:
            if self._compare_function(record["iso_code"], rc.code):
                return {'openerp_id': rc.id}
        return {'openerp_id': False}


@prestashopextend
class CountryImporter(prestashopextendImporter):
    _model_name = 'prestashopextend.res.country'


@job(default_channel='root.magentoextend')
def customer_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Customer """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(PartnerBatchImporter)
    importer.run(filters=filters)


class ResPartnerBackend(models.Model):
    _inherit = 'res.partner'

    owner_id = fields.Many2one('res.partner', string=u"Owner")
