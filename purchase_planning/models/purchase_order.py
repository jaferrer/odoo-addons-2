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

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        for rec in self:
            if rec.group_id:
                purchase_planning = self.env['period.planning'].search([('purchase_group_id', '=', rec.group_id.id)])
                purchase_planning.compute_state()
        return res

    def create(self, vals):
        res = super(PurchaseOrder, self).create(vals)
        for rec in self:
            if rec.group_id:
                purchase_planning = self.env['period.planning'].search([('purchase_group_id', '=', rec.group_id.id)])
                purchase_planning.compute_state()
        return res
