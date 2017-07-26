# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import fields, models, api


class IncompleteProductionProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    child_loc_id = fields.Many2one('stock.location', string="Child location", help="Source and destination locations of"
                                                                    " the automatically generated manufacturing order")


class IncompleteProductionProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _prepare_mo_vals(self,procurement):
        result = super(IncompleteProductionProcurementOrder, self)._prepare_mo_vals(procurement)
        if procurement.rule_id.child_loc_id.id:
            result['child_location_id'] = procurement.rule_id.child_loc_id.id
        return result
