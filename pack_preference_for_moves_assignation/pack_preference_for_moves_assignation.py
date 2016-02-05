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

from openerp import models, api, exceptions, _
from openerp.tools.float_utils import float_compare


class PackPreferenceStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def apply_removal_strategy(self, location, product, quantity, domain, removal_strategy):
        if removal_strategy == 'fifo':
            order = 'in_date, package_id, lot_id'
            return self._quants_get_order(location, product, quantity, domain, order)
        elif removal_strategy == 'lifo':
            order = 'in_date desc, package_id desc, lot_id desc'
            return self._quants_get_order(location, product, quantity, domain, order)
        raise exceptions.except_orm(_('Error!'), _('Removal strategy %s not implemented.' % (removal_strategy,)))
