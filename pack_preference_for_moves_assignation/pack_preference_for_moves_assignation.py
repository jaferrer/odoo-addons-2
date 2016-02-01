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

from openerp import models, fields, api, _
from openerp.osv import osv


class PackPreferenceStockQuant(models.Model):
    _inherit = 'stock.quant'

    fake_lot_id = fields.Integer(string=u"Fake lot id", compute='_compute_fake_data', store=True)
    fake_package_id = fields.Integer(string=u"Fake package id", compute='_compute_fake_data', store=True)

    @api.depends('lot_id', 'package_id')
    def _compute_fake_data(self):
        for rec in self:
            rec.fake_lot_id = rec.lot_id or 0
            rec.fake_package_id = rec.package_id or 0

    @api.model
    def apply_removal_strategy(self, location, product, quantity, domain, removal_strategy):
        if removal_strategy == 'fifo':
            order = 'in_date, fake_package_id, fake_lot_id, id'
            return self._quants_get_order(location, product, quantity, domain, order)
        elif removal_strategy == 'lifo':
            order = 'in_date desc, fake_package_id desc, fake_lot_id desc, id desc'
            return self._quants_get_order(location, product, quantity, domain, order)
        raise osv.except_osv(_('Error!'), _('Removal strategy %s not implemented.' % (removal_strategy,)))
