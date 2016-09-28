# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api


class RecomputeIrModel(models.Model):
    _inherit = 'ir.model'

    @api.multi
    def compute_parent_left_right(self):
        for rec in self:
            self.env[rec.model].sudo()._parent_store_compute()


class RecomputeParentPackages(models.Model):
    _inherit = 'stock.quant.package'

    @api.model
    def compute_parent_left_right(self):
        self.env['stock.quant.package'].sudo()._parent_store_compute()
