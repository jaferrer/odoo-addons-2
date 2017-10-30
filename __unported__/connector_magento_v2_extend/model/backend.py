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

from openerp import models, api
from .product import product_import_v2_batch, product_export_stock_level_v2_batch

_logger = logging.getLogger('magentoextend_backend')


class v2magentoextend_backend(models.Model):
    _inherit = 'magentoextend.backend'

    @api.multi
    def import_product_v2(self):
        new_ctx = dict(self.env.context)
        new_ctx['company_id'] = self.company_id.id
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)
        import_start_time = datetime.now()
        backend_id = self.id
        product = self.env['magentoextend2.product.product'].search([], limit=1, order="updated_at desc")
        from_date = None
        if product:
            from_date = product.updated_at
        for chunk_from, chunk_to in self.dates_chunk(from_date, import_start_time, timedelta(days=60)):
            product_import_v2_batch.delay(
                session, 'magentoextend2.product.product', backend_id,
                {'from_date': chunk_from,
                 'to_date': chunk_to}, priority=3)
            _logger.info("Date chunk %s -> %s", chunk_from, chunk_to)
        return True

    @api.model
    def cron_import_product_v2(self, id):
        back = self.env['magentoextend.backend'].search([('id', '=', id)])
        if back:
            back.import_product_v2()

    @api.multi
    def export_stock_level_v2(self):
        new_ctx = dict(self.env.context)
        new_ctx['company_id'] = self.company_id.id
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)
        backend_id = self.id
        product_export_stock_level_v2_batch.delay(
            session, 'magentoextend2.product.product', backend_id, priority=3)
        return True

    @api.model
    def cron_export_stock_level_v2(self, el_id):
        back = self.env['magentoextend.backend'].search([('id', '=', el_id)])
        if back:
            back.export_stock_level_v2()
