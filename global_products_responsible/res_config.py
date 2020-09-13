# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields

PARAM_KEY = 'stock_global_products_responsible.global_products_responsible_id'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    global_products_responsible_id = fields.Many2one('res.users', string='Responsible for products configuration',
                                                     help="This user will be responsible of the next activities related"
                                                          " to logistic operations for all the products.",
                                                     config_parameter=PARAM_KEY)
