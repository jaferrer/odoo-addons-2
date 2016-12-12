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

    opmsg_min_late_delay = fields.Integer(string="Delay to be late (in days)",
                                          help="Minimum delay to create an operational message specifying that the "
                                               "purchase order line is late. If the planned date is less than this "
                                               "number of days beyond the required date, no message will be displayed."
                                               "\nDefaults to 1 day.")
    opmsg_min_early_delay = fields.Integer(string="Delay to be early (in days)",
                                           help="Minimum delay to create an operational message specifying that the "
                                                "purchase order line is early. If the planned date is less than this "
                                                "number of days before the required date, no message will be displayed."
                                                "\nDefaults to 7 days.")
    delta_begin_grouping_period = fields.Integer(string="Delta begin grouping period",
                                                 help="Grouping periods will be centered on the date of tomorrow, "
                                                      "increased by this delta")
    ignore_past_procurements = fields.Boolean(string="Ignore past procurements", help="Used for the purchase planner")

    @api.multi
    def get_default_opmsg_min_late_delay(self):
        opmsg_min_late_delay = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.opmsg_min_late_delay", default=1)
        return {'opmsg_min_late_delay': int(opmsg_min_late_delay)}

    @api.multi
    def set_opmsg_min_late_delay(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.opmsg_min_late_delay",
                                        record.opmsg_min_late_delay or '1')

    @api.multi
    def get_default_opmsg_min_early_delay(self):
        opmsg_min_early_delay = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.opmsg_min_early_delay", default=7)
        return {'opmsg_min_early_delay': int(opmsg_min_early_delay)}

    @api.multi
    def set_opmsg_min_early_delay(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.opmsg_min_early_delay",
                                        record.opmsg_min_early_delay or '7')

    @api.multi
    def get_default_delta_begin_grouping_period(self):
        delta_begin_grouping_period = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.delta_begin_grouping_period", default=0)
        return {'delta_begin_grouping_period': int(delta_begin_grouping_period)}

    @api.multi
    def set_delta_begin_grouping_period(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.delta_begin_grouping_period",
                                        record.delta_begin_grouping_period or '0')

    @api.multi
    def get_default_ignore_past_procurements(self):
        ignore_past_procurements = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.ignore_past_procurements", default=False)
        return {'ignore_past_procurements': bool(ignore_past_procurements)}

    @api.multi
    def set_ignore_past_procurements(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.ignore_past_procurements",
                                        record.ignore_past_procurements or '')
