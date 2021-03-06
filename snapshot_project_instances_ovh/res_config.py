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

from openerp import models, fields, api
from ovh import Client


class OvhParameters(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'ovh.parameters'

    area = fields.Char(string="Area", default='ovh-eu')
    app_key = fields.Char(string="Application key",
                          help="Extra informations at https://eu.api.ovh.com/createApp/")
    app_secret = fields.Char(string="Application secret",
                             help="Extra informations at https://eu.api.ovh.com/createApp/")
    consumer_key = fields.Char(string="Consumer key")
    min_hour_snapshot = fields.Integer(string="Minimum hour for snapshot (GMT)")
    max_hour_snapshot = fields.Integer(string="Maximum hour for snapshot (GMT)")

    @api.multi
    def get_default_area(self):
        area = self.env['ir.config_parameter'].get_param("snapshot_project_instances_ovh.area", default='')
        return {'area': str(area)}

    @api.multi
    def set_area(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.area", record.area or '')

    @api.multi
    def get_default_app_key(self):
        app_key = self.env['ir.config_parameter'].get_param("snapshot_project_instances_ovh.app_key", default='')
        return {'app_key': str(app_key)}

    @api.multi
    def set_app_key(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.app_key", record.app_key or '')

    @api.multi
    def get_default_app_secret(self):
        app_secret = self.env['ir.config_parameter'].get_param("snapshot_project_instances_ovh.app_secret", default='')
        return {'app_secret': str(app_secret)}

    @api.multi
    def set_app_secret(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.app_secret", record.app_secret or '')

    @api.multi
    def get_default_max_hour_snapshot(self):
        max_hour_snapshot = self.env['ir.config_parameter'].get_param("snapshot_project_instances_ovh.max_hour_snapshot",
                                                                 default=0)
        return {'max_hour_snapshot': int(max_hour_snapshot)}

    @api.multi
    def set_max_hour_snapshot(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.max_hour_snapshot", record.max_hour_snapshot or '0')

    @api.multi
    def get_default_min_hour_snapshot(self):
        min_hour_snapshot = self.env['ir.config_parameter']. \
            get_param("snapshot_project_instances_ovh.min_hour_snapshot", default=0)
        return {'min_hour_snapshot': int(min_hour_snapshot)}

    @api.multi
    def set_min_hour_snapshot(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.min_hour_snapshot",
                                        record.min_hour_snapshot or '0')

    @api.multi
    def get_default_consumer_key(self):
        consumer_key = self.env['ir.config_parameter'].get_param("snapshot_project_instances_ovh.consumer_key",
                                                                 default='')
        return {'consumer_key': str(consumer_key)}

    @api.multi
    def set_consumer_key(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("snapshot_project_instances_ovh.consumer_key", record.consumer_key or '')

    @api.multi
    def ask_for_snapshots_multi(self):
        self.ask_for_snapshots_model()

    @api.model
    def ask_for_snapshots_model(self):
        self.env['snapshot.request.line'].search([]).ask_for_snapshots()
