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

    delete_moves_cancelled_by_planned = fields.Boolean(string=u"Delete moves and procurements cancelled "
                                                              u"by planner")
    relative_stock_delta = fields.Boolean(string=u"Relative tock delta allowed (%)")
    absolute_stock_delta = fields.Boolean(string=u"Absolute tock delta allowed (product UoM)")

    @api.multi
    def get_default_delete_moves_cancelled_by_planned(self):
        delete_moves_cancelled_by_planned = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.delete_moves_cancelled_by_planned", default=False)
        return {'delete_moves_cancelled_by_planned': bool(delete_moves_cancelled_by_planned)}

    @api.multi
    def set_delete_moves_cancelled_by_planned(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.delete_moves_cancelled_by_planned",
                                        record.delete_moves_cancelled_by_planned or '')

    @api.multi
    def get_default_relative_stock_delta(self):
        relative_stock_delta = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.relative_stock_delta", default=0)
        return {'relative_stock_delta': bool(relative_stock_delta)}

    @api.multi
    def set_relative_stock_delta(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.relative_stock_delta",
                                        record.relative_stock_delta or '')

    @api.multi
    def get_default_absolute_stock_delta(self):
        absolute_stock_delta = self.env['ir.config_parameter'].get_param(
            "stock_procurement_just_in_time.absolute_stock_delta", default=0)
        return {'absolute_stock_delta': bool(absolute_stock_delta)}

    @api.multi
    def set_absolute_stock_delta(self):
        config_parameters = self.env["ir.config_parameter"]
        for record in self:
            config_parameters.set_param("stock_procurement_just_in_time.absolute_stock_delta",
                                        record.absolute_stock_delta or '')
