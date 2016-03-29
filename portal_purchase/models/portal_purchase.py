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

from openerp import models, fields, api


class PortalPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    validated_by_supplier = fields.Boolean(string="Validated by the supplier", readonly=True,
                                           track_visibility='on_change')

    @api.multi
    def action_supplier_validate(self):
        self.ensure_one()
        self.validated_by_supplier = True


class PortalPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    validated_by_supplier = fields.Boolean(string="Validated by the supplier", readonly=True,
                                           related='order_id.validated_by_supplier')
