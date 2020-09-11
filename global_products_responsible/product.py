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

from odoo.addons.global_products_responsible.res_config import PARAM_KEY

from odoo import fields, models, api


class ProductTamplate(models.Model):
    _inherit = 'product.template'

    responsible_id = fields.Many2one('res.users', compute='_compute_responsible_id', required=False)

    @api.multi
    def _compute_responsible_id(self):
        global_responsible = self.env['res.users']
        global_responsible_id = int(self.env['ir.config_parameter'].sudo().get_param(PARAM_KEY) or '0')
        if global_responsible_id:
            global_responsible = self.env['res.users'].browse(global_responsible_id)
        responsible = global_responsible or self.env.user
        for rec in self:
            rec.responsible_id = responsible
