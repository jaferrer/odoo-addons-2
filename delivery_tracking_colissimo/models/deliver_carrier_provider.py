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

from odoo.addons.delivery_tracking.models.delivery_carrier_provider import _PROVIDER
from odoo import models, fields

_PROVIDER.append(('colissimo', "Colissimo"))


class DeliveryCarrierProvider(models.Model):
    _inherit = 'delivery.carrier.provider'

    api_login_colissimo = fields.Char("Login Colissimo")
    api_password_colissimo = fields.Char("Password Colissimo")
