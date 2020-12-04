# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, fields, api


class ProductProductExporter(models.TransientModel):
    _name = 'product.product.exporter.wizard'

    def _default_backend(self):
        return self.env['magento.backend'].search([], limit=1).id

    product_id = fields.Many2one('product.product')
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        default=_default_backend,
        string='Backend',
    )

    @api.multi
    def apply(self):
        self.env['magento.product.product'].get_or_create_binding(self.product_id, self.backend_id)
        # TODO trigger listener or manually trigger export
