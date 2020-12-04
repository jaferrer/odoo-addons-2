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
from odoo import models, api


class MagentoBinding(models.AbstractModel):
    _inherit = 'magento.binding'

    @api.model
    def get_or_create_binding(self, record, backend_record):
        """ Return the existing binding for a single record, or create it if it doesn't exist """
        record.ensure_one()
        binding = self.with_context(active_test=False).search([
            ('odoo_id', '=', record.id),
            ('backend_id', '=', backend_record.id),
        ])
        if not binding:
            self.create({
                'backend_id': backend_record.id,
                'odoo_id': record.id,
            })

        return binding
