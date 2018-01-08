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
    ignore_past_procurements = fields.Boolean(string="Ignore past procurements",
                                              help="Used for the purchase planner")
    fill_orders_in_separate_jobs = fields.Boolean(string="Fill draft orders in separate jobs",
                                                  help="Used for the purchase planner")
    redistribute_procurements_in_separate_jobs = fields.Boolean(string="Redistribute procurements in separate jobs",
                                                                help="Used for the purchase planner")
    config_sellers_manually = fields.Boolean(string="Configure purchase scheduler manually for each supplier")
    order_group_period = fields.Many2one('procurement.time.frame', "Default order grouping period")
    nb_max_draft_orders = fields.Integer(string="Default maximal number of draft purchase orders for each new supplier")
    nb_days_scheduler_frequency = fields.Integer(string="Default scheduler frequency (in days)")

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

    @api.multi
    def get_default_fill_orders_in_separate_jobs(self):
        fill_orders_in_separate_jobs = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.fill_orders_in_separate_jobs", default=False)
        return {'fill_orders_in_separate_jobs': bool(fill_orders_in_separate_jobs)}

    @api.multi
    def set_fill_orders_in_separate_jobs(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.fill_orders_in_separate_jobs",
                                        record.fill_orders_in_separate_jobs or '')

    @api.multi
    def get_default_redistribute_procurements_in_separate_jobs(self):
        redistribute_procurements_in_separate_jobs = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.redistribute_procurements_in_separate_jobs", default=False)
        return {'redistribute_procurements_in_separate_jobs': bool(redistribute_procurements_in_separate_jobs)}

    @api.multi
    def set_redistribute_procurements_in_separate_jobs(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.redistribute_procurements_in_separate_jobs",
                                        record.redistribute_procurements_in_separate_jobs or '')

    @api.multi
    def get_default_config_sellers_manually(self):
        config_sellers_manually = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.config_sellers_manually", default=False)
        return {'config_sellers_manually': bool(config_sellers_manually)}

    @api.multi
    def set_config_sellers_manually(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.config_sellers_manually",
                                        record.config_sellers_manually or '')

    @api.multi
    def get_default_order_group_period(self):
        order_group_period_id = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.order_group_period", default=False)
        order_group_period = order_group_period_id and int(order_group_period_id) or False
        return {'order_group_period': order_group_period}

    @api.multi
    def set_order_group_period(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.order_group_period",
                                        record.order_group_period and record.order_group_period.id or '')

    @api.multi
    def get_default_nb_max_draft_orders(self):
        nb_max_draft_orders = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.nb_max_draft_orders", default=0)
        return {'nb_max_draft_orders': int(nb_max_draft_orders)}

    @api.multi
    def set_nb_max_draft_orders(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.nb_max_draft_orders",
                                        record.nb_max_draft_orders or '0')

    @api.multi
    def get_default_nb_days_scheduler_frequency(self):
        nb_days_scheduler_frequency = self.env['ir.config_parameter'].get_param(
            "purchase_procurement_just_in_time.nb_days_scheduler_frequency", default=0)
        return {'nb_days_scheduler_frequency': int(nb_days_scheduler_frequency)}

    @api.multi
    def set_nb_days_scheduler_frequency(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("purchase_procurement_just_in_time.nb_days_scheduler_frequency",
                                        record.nb_days_scheduler_frequency or '0')
