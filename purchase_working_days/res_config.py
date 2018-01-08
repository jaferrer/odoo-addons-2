# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class PurchaseWorkingDaysConfig(models.TransientModel):
    _inherit = 'purchase.config.settings'

    purchase_lead_time = fields.Integer(string="Default purchase lead time for each new supplier")

    @api.multi
    def get_default_purchase_lead_time(self):
        purchase_lead_time = self.env['ir.config_parameter'].get_param("purchase_working_days.purchase_lead_time",
                                                                       default=0)
        return {'purchase_lead_time': int(purchase_lead_time)}

    @api.multi
    def set_purchase_lead_time(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_working_days.purchase_lead_time", record.purchase_lead_time or '0')
