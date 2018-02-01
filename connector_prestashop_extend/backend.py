# -*- coding: utf-8 -*-
#
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import openerp.addons.connector.backend as backend

prestashopextend = backend.Backend('prestashopextend')
""" Generic prestashopextend Backend """

prestashop_1_5_0_0 = backend.Backend(parent=prestashopextend, version='1.5')
# version 1.6.0.9 - 1.6.0.10
prestashop_1_6_0_9 = backend.Backend(parent=prestashopextend, version='1.6.0.9')
# version >= 1.6.0.11
prestashop_1_6_0_11 = backend.Backend(parent=prestashopextend, version='1.6.0.11')
# version >= 1.6.1.2
prestashop_1_6_1_2 = backend.Backend(parent=prestashopextend, version='1.6.1.2')
