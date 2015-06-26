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


class purchase_jit_config(models.TransientModel):
    _inherit = 'purchase.config.settings'

    opmsg_min_late_delay = fields.Integer("Delay to be late (in days)",
                                          help="Minimum delay to create an operational message specifying that the "
                                               "purchase order line is late. If the planned date is less than this "
                                               "number of days beyond the required date, no message will be displayed."
                                               "\nDefaults to 1 day.")
    opmsg_min_early_delay = fields.Integer("Delay to be early (in days)",
                                          help="Minimum delay to create an operational message specifying that the "
                                               "purchase order line is early. If the planned date is less than this "
                                               "number of days before the required date, no message will be displayed."
                                               "\nDefaults to 7 days.")

    @api.multi
    def get_default_opmsg_min_late_delay(self):
        opmsg_min_late_delay = self.env['ir.config_parameter'].get_param(
                                                   "purchase_procurement_just_in_time.opmsg_min_late_delay", default=1)
        return {'opmsg_min_late_delay': int(opmsg_min_late_delay)}

    @api.multi
    def get_default_opmsg_min_early_delay(self):
        opmsg_min_early_delay = self.env['ir.config_parameter'].get_param(
                                                   "purchase_procurement_just_in_time.opmsg_min_early_delay", default=7)
        return {'opmsg_min_early_delay': int(opmsg_min_early_delay)}

    @api.multi
    def set_opmsg_min_late_delay(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.opmsg_min_late_delay",
                                        record.opmsg_min_late_delay or "1")

    @api.multi
    def set_opmsg_min_early_delay(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.opmsg_min_early_delay",
                                        record.opmsg_min_early_delay or "7")

