# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


class RestaurantAllergen(models.Model):
    _name = 'restaurant.allergen'

    name = fields.Char(string=u"Name", translate=True)
    active = fields.Boolean(string=u"Active", default=True)


class RestaurantAllergenProductTemplate(models.Model):
    _inherit = 'product.template'

    allergen_ids = fields.Many2many('restaurant.allergen', string=u"Allergens")


class LaunchAllergensReport(models.TransientModel):
    _name = 'launch.allergens.report'

    def _get_default_language_id(self):
        return self.env['res.lang'].search([('code', '=', self.env.user.lang)], limit=1)

    language_id = fields.Many2one('res.lang', string=u"Language", domain=[('translatable', '=', True)],
                                  default=_get_default_language_id, required=True)

    @api.multi
    def launch_allergens_report(self):
        self.ensure_one()
        return self.env['report'].get_action(self, 'allergens_report')
