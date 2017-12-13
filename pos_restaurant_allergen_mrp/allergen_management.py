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


class RestaurantAllergenProductTemplate(models.Model):
    _inherit = 'product.template'

    compute_allergens = fields.Boolean(string=u"Compute allergens", compute='_compute_allergens', store=True)
    manufactured_allergen_ids = fields.Many2many('restaurant.allergen', string=u"Allergens",
                                                 compute='_compute_manufactured_allergen_ids')

    @api.multi
    @api.depends('bom_ids')
    def _compute_allergens(self):
        for rec in self:
            rec.compute_allergens = bool(rec.bom_ids)

    @api.multi
    def compute_effective_allergens(self):
        self.ensure_one()
        bom_id = self.env['mrp.bom']._bom_find(product_tmpl_id=self.id)
        if bom_id:
            manufactured_allergens = self.env['restaurant.allergen']
            bom = self.env['mrp.bom'].search([('id', '=', bom_id)])
            for line in bom.bom_line_ids:
                manufactured_allergens |= line.product_id.product_tmpl_id.compute_effective_allergens()
            return manufactured_allergens
        else:
            return self.allergen_ids

    @api.multi
    def _compute_manufactured_allergen_ids(self):
        for rec in self:
            rec.manufactured_allergen_ids = rec.compute_effective_allergens()
