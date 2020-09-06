# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class StockMandatoryOrderpointsResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mandatory_orderpoint_location_ids = fields.Many2many('stock.location', string=u"Mandatory Orderpoint Locations")

    @api.model
    def get_values(self):
        res = super(StockMandatoryOrderpointsResConfigSettings, self).get_values()
        mandatory_orderpoint_location_ids = self.env['ir.config_parameter'].sudo(). \
            get_param('stock_mandatory_orderpoints.mandatory_orderpoint_location_ids') or '[]'
        res.update(
            mandatory_orderpoint_location_ids=eval(mandatory_orderpoint_location_ids),
        )
        return res

    @api.multi
    def set_values(self):
        super(StockMandatoryOrderpointsResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        mandatory_orderpoint_location_ids = self.mandatory_orderpoint_location_ids.ids or []
        param.set_param('stock_mandatory_orderpoints.mandatory_orderpoint_location_ids',
                        mandatory_orderpoint_location_ids)
