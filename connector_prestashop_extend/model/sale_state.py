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
from ..unit.importer import (DelayedBatchImporter, prestashopextendImporter, TranslatableRecordImporter, DirectBatchImporter)

_logger = logging.getLogger(__name__)


class SaleOrderState(models.Model):
    _name = 'sale.order.state'

    name = fields.Char('Name', translate=True)
    owner_id = fields.Many2one('res.partner', string=u"Owner")


class PrestashopShop(models.Model):
    _name = 'prestashopextend.sale.order.state'
    _inherit = 'prestashopextend.binding.odoo'
    _inherits = {'sale.order.state': 'openerp_id'}

    @api.multi
    @api.depends('shop_group_id', 'shop_group_id.backend_id')
    def _compute_backend_id(self):
        self.backend_id = self.shop_group_id.backend_id.id

    openerp_id = fields.Many2one(comodel_name='sale.order.state',
                                 string='state',
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

    name = fields.Char(related="openerp_id.name")


@prestashopextend
class SaleOrderStateAdapter(GenericAdapter):
    _model_name = 'prestashopextend.sale.order.state'
    _prestashopextend_model = 'order_states'


@prestashopextend
class SaleOrderStateMapper(ImportMapper):
    _model_name = 'prestashopextend.sale.order.state'

    direct = [
        ('name', 'name'),
    ]

    @mapping
    def backend_id(self, record):
        return {'backend_id': self.backend_record.id}

    @mapping
    def owner_id(self, record):
        return {'owner_id': self.backend_record.connector_id.home_id.partner_id.id}

    @mapping
    def prestashopextend_id(self, record):
        return {'prestashopextend_id': record["id"]}



@prestashopextend
class SaleOrderStateImporter(TranslatableRecordImporter):
    """ Import one translatable record """
    _model_name = [
        'prestashopextend.sale.order.state',
    ]

    _translatable_fields = {
        'prestashopextend.sale.order.state': [
            'name',
        ],
    }


@prestashopextend
class SaleOrderStateBatchImporter(DelayedBatchImporter):
    _model_name = 'prestashopextend.sale.order.state'
    _prestashopextend_model = 'order_states'


@job(default_channel='root.prestashopextend')
def sale_state_import_batch(session, model_name, backend_id, filters=None):
    """ Prepare the import of Customer """
    env = get_environment(session, model_name, backend_id)
    importer = env.get_connector_unit(SaleOrderStateBatchImporter)
    importer.run(filters=filters)
