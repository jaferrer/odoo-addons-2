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

from odoo import fields, models, api


class PosCategory(models.Model):
    _inherit = "pos.category"

    need_a_customer = fields.Boolean('Need a customer')


class ProductTemplate(models.Model):
    _inherit = "product.template"

    need_a_customer = fields.Boolean('Need a customer')

    required_customer = fields.Boolean("Customer in POS is required", compute='_compute_required_customer')

    @api.multi
    def _compute_required_customer(self):
        for rec in self:
            required_customer = rec.need_a_customer
            categ = rec.pos_categ_id
            while categ and not required_customer:
                required_customer = categ.need_a_customer
                categ = categ.parent_id
            rec.required_customer = required_customer
