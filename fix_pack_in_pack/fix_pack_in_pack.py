# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import time

from openerp.osv import osv
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID


class stock_quant_package_fix(osv.osv):
    _inherit = 'stock.quant.package'

    def _get_packages(self, cr, uid, ids, context=None):
        """Returns packages from quants for store"""
        res = set()
        for quant in self.browse(cr, uid, ids, context=context):
            pack = quant.package_id
            while pack:
                res.add(pack.id)
                pack = pack.parent_id
        return list(res)
