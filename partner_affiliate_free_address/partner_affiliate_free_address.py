# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        result = super(ResPartner, self).onchange_parent_id()
        address_fields = self._address_fields()
        if result.get('value'):
            result['value'] = {key: result['value'][key] for key in result['value'] if key not in address_fields}
        return result
