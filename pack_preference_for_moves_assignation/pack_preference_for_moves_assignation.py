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
            order = 'in_date, package_id, lot_id, id'
            return self._quants_get_order(location, product, quantity, domain, order)
        elif removal_strategy == 'lifo':
            order = 'in_date desc, package_id desc, lot_id desc, id desc'
            return self._quants_get_order(location, product, quantity, domain, order)
        raise exceptions.except_orm(_('Error!'), _('Removal strategy %s not implemented.' % (removal_strategy,)))

    @api.model
    def _quants_get_order(self, location, product, quantity, domain=[], orderby='in_date'):
        """
        Implementation of removal strategies.
        If it can not reserve, it will return a tuple (None, qty)
        """
        domain += location and [('location_id', 'child_of', location.id)] or []
        domain += [('product_id', '=', product.id)]
        if self.env.context.get('force_company'):
            domain += [('company_id', '=', self.env.context['force_company'])]
        else:
            domain += [('company_id', '=', self.env.user.company_id.id)]
        res = []
        while float_compare(quantity, 0, precision_rounding=product.uom_id.rounding) > 0:
            quants = self.search(domain, order=orderby)
            if not quants:
                res.append((None, quantity))
                break
            for quant in quants:
                rounding = product.uom_id.rounding
                if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    res += [(quant, abs(quant.qty))]
                    quantity -= abs(quant.qty)
                elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                    res += [(quant, quantity)]
                    quantity = 0
                    break
        return res
