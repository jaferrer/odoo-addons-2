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

from odoo import models, fields, api


class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    avis_verifies_site_reviews_url = fields.Char(u"Avis-verifies' site review URL")

    @api.model
    def get_default_avis_verifies_site_reviews_url(self, fields):
        return {
            'avis_verifies_site_reviews_url': self.env['ir.config_parameter'].get_param(
                'avis.verifies.site_reviews_url')
        }

    @api.multi
    def set_avis_verifies_site_reviews_url(self):
        self.ensure_one()
        if self.avis_verifies_site_reviews_url:
            self.env['ir.config_parameter'].set_param('avis.verifies.site_reviews_url',
                                                      self.avis_verifies_site_reviews_url)
