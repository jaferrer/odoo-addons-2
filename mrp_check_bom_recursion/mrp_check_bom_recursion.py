# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, exceptions, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.multi
    def _check_bom_recursion(self, products=None):
        """Raise an exception if one these BoMs is recursive"""
        if products is None:
            products = self.env['product.product']
        for rec in self:
            for bom_line in rec.bom_line_ids:
                if bom_line.product_id in products:
                    raise exceptions.except_orm(_(u"Error"),
                                                _(u"This BoM is recursive. Product %s found at least twice") %
                                                bom_line.product_id.display_name)
                for product_bom in self.env['mrp.bom'].search([('product_id', '=', bom_line.product_id.id)]):
                    product_bom._check_bom_recursion(products=products | bom_line.product_id)

    @api.model
    def create(self, vals):
        res = super(MrpBom, self).create(vals)
        res._check_bom_recursion()
        return res

    @api.multi
    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        if "product_id" in vals or "product_tmpl_id" in vals or "bom_line_ids" in vals:
            self._check_bom_recursion()
        return res


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.model
    def create(self, vals):
        res = super(MrpBomLine, self).create(vals)
        res.bom_id._check_bom_recursion()
        return res

    @api.multi
    def write(self, vals):
        res = super(MrpBomLine, self).write(vals)
        for rec in self:
            if "product_id" in vals or "bom_id" in vals:
                rec.bom_id._check_bom_recursion()
        return res
