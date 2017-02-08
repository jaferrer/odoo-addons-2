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
from datetime import datetime
from datetime import timedelta

from openerp.addons.connector.session import ConnectorSession

from openerp import models, api, fields
# from .product_category import category_import_batch
from .product import product_import_batch, product_export_stock_level_batch
from .customer import customer_import_batch

# from .sale import sale_order_import_batch

_logger = logging.getLogger('magentoextend_backend')


class magentoextend_backend(models.Model):
    _name = 'magentoextend.backend'
    _inherit = 'connector.backend'
    _description = 'Magento Backend Configuration'
    name = fields.Char(string='name')
    _backend_type = 'magentoextend'

    connector_id = fields.Many2one('backend.connector.info.line', string=u"connector line")

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        help='Warehouse used to compute the '
             'stock quantities.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='warehouse_id.company_id',
        string='Company',
        readonly=True,
    )

    version = fields.Selection([('v1', 'V1')], 'Version', default="v1")

    default_lang_id = fields.Many2one(
        comodel_name='res.lang',
        string='Default Language',
        help="If a default language is selected, the records "
             "will be imported in the translation of this language.\n"
             "Note that a similar configuration exists "
             "for each storeview.",
    )

    @api.multi
    def get_customer_ids(self, data):
        customer_ids = [x['id'] for x in data['customers']]
        customer_ids = sorted(customer_ids)
        return customer_ids

    @api.multi
    def test_connection(self):
        return True

    @api.multi
    def import_customer(self):
        new_ctx = dict(self.env.context)
        new_ctx['company_id'] = self.company_id.id
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)
        import_start_time = datetime.now()
        backend_id = self.id
        partner = self.env['magentoextend.res.partner'].search([], limit=1, order="updated_at desc")
        from_date = None
        if partner:
            from_date = partner.updated_at

        for chunk_from, chunk_to in self.dates_chunk(from_date, import_start_time, timedelta(days=60)):
            customer_import_batch.delay(
                session, 'magentoextend.res.partner', backend_id,
                {'from_date': chunk_from,
                 'to_date': chunk_to}, priority=3)
            _logger.info("Date chunk %s -> %s", chunk_from, chunk_to)
        return True

    @api.model
    def cron_import_customer(self, id):
        back = self.env['magentoextend.backend'].search([('id', '=', id)])
        if back:
            back.import_customer()

    def dates_chunk(self, from_date, to_date, delta=timedelta(days=120)):
        frmt = '%Y-%m-%d %H:%M:%S'
        # Date de départ par défaut = 2 mois avant la mise en service du
        # site Airsoft Entrepot sous Magento
        if not from_date:
            from_date = datetime.strptime('2013-10-01 00:00:00', frmt)
        else:
            from_date = datetime.strptime(from_date, frmt)

        if to_date - from_date > delta:
            # initialize, [a, b] is the first chunk
            a, b = from_date, from_date + delta

            while True:
                yield a, b
                if b == to_date:
                    # We have reached and returned the last chunk, stop the loop
                    break
                else:
                    # Normal execution, prepare from and to dates of the next chunk
                    a = b
                    b = min(b + delta, to_date)
        else:
            yield from_date, to_date

    @api.multi
    def import_product(self):
        new_ctx = dict(self.env.context)
        new_ctx['company_id'] = self.company_id.id
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)
        import_start_time = datetime.now()
        backend_id = self.id
        product = self.env['magentoextend.product.product'].search([], limit=1, order="updated_at desc")
        from_date = None
        if product:
            from_date = product.updated_at
        for chunk_from, chunk_to in self.dates_chunk(from_date, import_start_time, timedelta(days=60)):
            product_import_batch.delay(
                session, 'magentoextend.product.product', backend_id,
                {'from_date': chunk_from,
                 'to_date': chunk_to}, priority=3)
            _logger.info("Date chunk %s -> %s", chunk_from, chunk_to)
        return True

    @api.model
    def cron_import_product(self, id):
        back = self.env['magentoextend.backend'].search([('id', '=', id)])
        if back:
            back.import_product()

    @api.multi
    def export_stock_level(self):
        new_ctx = dict(self.env.context)
        new_ctx['company_id'] = self.company_id.id
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)
        backend_id = self.id
        product_export_stock_level_batch.delay(
            session, 'magentoextend.product.product', backend_id, priority=3)
        return True

    @api.model
    def cron_export_stock_level(self, el_id):
        back = self.env['magentoextend.backend'].search([('id', '=', el_id)])
        if back:
            back.export_stock_level()
