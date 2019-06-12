# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import models, fields, api


class ResPartnerWithAddressFromProvider(models.Model):
    _inherit = 'res.partner'

    address_provider = fields.Many2one('res.partner.address.provider', u"Adresse")

    @api.onchange('address_provider')
    def _onchange_address_provider(self):
        if not self.address_provider or not self.address_provider.street:
            self.street = ''
        else:
            self.street = " ".join(
                [self.address_provider.houseNumber or '', self.address_provider.street or '']
            ).strip()
        self.zip = self.address_provider.postalCode
        self.city = self.address_provider.city
        self.country = self.address_provider.country
