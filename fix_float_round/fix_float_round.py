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

import openerp

old_float_round = openerp.tools.float_utils.float_round


def new_float_round(value, precision_digits=None, precision_rounding=None, rounding_method='HALF-UP'):
    return float(str(old_float_round(value, precision_digits=precision_digits, precision_rounding=precision_rounding,
                                     rounding_method=rounding_method)))


openerp.tools.float_utils.float_round = new_float_round
