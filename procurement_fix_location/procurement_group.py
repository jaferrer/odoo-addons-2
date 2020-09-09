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
from odoo import models, api, _ as _t
from odoo.exceptions import UserError


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def run(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        rule = self._get_rule(product_id, location_id, values)
        if not rule:
            raise UserError(
                _t("Error, the partner doesn't have stock location. \n "
                   "You can add it in his customer file (inside Sales & Purchase page)."))
        super(ProcurementGroup, self).run(product_id, product_qty, product_uom, location_id, name, origin, values)
