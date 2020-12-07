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
    def get_or_create_bindings(self, records, backend_record):
        """ Return the existing binding for some records, or create them if they don't exist """
        bindings = self.browse()
        for rec in records:
            binding = self.with_context(active_test=False).search([
                ('odoo_id', '=', rec.id),
                ('backend_id', '=', backend_record.id),
            ])
            if not binding:
                binding = self.create({
                    'backend_id': backend_record.id,
                    'odoo_id': rec.id,
                })
            bindings |= binding

        return bindings
