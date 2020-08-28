# -*- coding: utf8 -*-
#
# Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp import models, api


class Purchase(osv.osv):

    _inherit = ['purchase.order']
    _description = "Purchase Order"
    _order = 'date_order desc, id desc'


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        super_result = super(PurchaseOrderLine, self).read(fields=fields, load=load)
        if 'taxes_id' in fields:
            taxes_names_dict = {tax_id: name for (tax_id, name) in self.env['account.tax'].search([]).name_get()}
            result = []
            for res in super_result:
                res['taxes_id__display'] = ', '.join([taxes_names_dict[tax.id] for tax in self.browse(res['id']).taxes_id])
                result += [res]
            return result
        return super_result
