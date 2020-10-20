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


class StockProcurementJitConfig(models.TransientModel):
    _inherit = 'stock.config.settings'

    consider_end_contract_effect = fields.Boolean(string=u"Consider end contract effects")
    relative_stock_delta = fields.Float(string=u"Relative stock delta allowed (%)")
    absolute_stock_delta = fields.Float(string=u"Absolute stock delta allowed (product UoM)")
    keep_stock_controller_lines_for = fields.Integer(string=u"Keep stock controller lines for (in days)")

    @api.multi
    def get_default_consider_end_contract_effect(self):
        consider_end_contract_effect = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.consider_end_contract_effect", default=False)
        return {'consider_end_contract_effect': bool(consider_end_contract_effect)}

    @api.multi
    def set_consider_end_contract_effect(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.consider_end_contract_effect",
                                        record.consider_end_contract_effect or '')

    @api.multi
    def get_default_relative_stock_delta(self):
        relative_stock_delta = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.relative_stock_delta", default=0.0) or 0.0
        return {'relative_stock_delta': float(relative_stock_delta)}

    @api.multi
    def set_relative_stock_delta(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.relative_stock_delta",
                                        record.relative_stock_delta or '0.0')

    @api.multi
    def get_default_absolute_stock_delta(self):
        absolute_stock_delta = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.absolute_stock_delta", default=0) or 0.0
        return {'absolute_stock_delta': float(absolute_stock_delta)}

    @api.multi
    def set_absolute_stock_delta(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.absolute_stock_delta",
                                        record.absolute_stock_delta or '0.0')

    @api.multi
    def get_default_keep_stock_controller_lines_for(self):
        keep_stock_controller_lines_for = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.keep_stock_controller_lines_for", default=0) or 0
        return {'keep_stock_controller_lines_for': int(keep_stock_controller_lines_for)}

    @api.multi
    def set_keep_stock_controller_lines_for(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.keep_stock_controller_lines_for",
                                        record.keep_stock_controller_lines_for or '0')
