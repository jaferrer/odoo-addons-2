# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import fields, models, api

class sirail_production_bom_line (models.Model):
    _inherit = "mrp.bom.line"

    product_father_id = fields.Many2one('product.product', string=u"Produit père")
    father_line_ids = fields.Many2many('mrp.bom.line', compute="_get_father_bom_lines")

    @api.multi
    def _get_father_bom_lines(self, context=None):
        """If the BOM line refers to a BOM, return the ids of the child BOM lines"""
        for rec in self:
            parent_ids = []
            parent_product = rec.bom_id.product_id
            parent_product_tmpl = rec.bom_id.product_tmpl_id
            if parent_product:
                parent_ids.append(parent_product.id)
            elif parent_product_tmpl:
                products = self.env['product.product'].search([('product_tmpl_id','=',parent_product_tmpl)])
                parent_ids += products.ids
            parent_lines = self.search([('product_id','in',parent_ids)])
            rec.father_line_ids = [(6, 0, [p.id for p in parent_lines])]


