# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class ApiYousignConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    # Configuration Yousign
    yousign_api_key = fields.Char("Clef API Yousign", config_parameter='yousign_api_key')
    yousign_webhook = fields.Char("Clef Webhook", config_parameter='yousign_webhook')
    yousign_staging = fields.Boolean("Staging env", config_parameter='yousign_staging')
