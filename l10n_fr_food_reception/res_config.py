# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class FoodReceptionStockSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    force_fill_reception_temperatures = fields.Boolean(string=u"Force to fill reception temperatures if needed")

    @api.multi
    def get_default_force_fill_reception_temperatures(self):
        value = self.env['ir.config_parameter'].get_param('l10n_food_reception.force_fill_reception_temperatures',
                                                          default=False)
        return {'force_fill_reception_temperatures': value and bool(value) or False}

    @api.multi
    def set_force_fill_reception_temperatures(self):
        for record in self:
            self.env['ir.config_parameter'].set_param('l10n_food_reception.force_fill_reception_temperatures',
                                                      record.force_fill_reception_temperatures or False)
