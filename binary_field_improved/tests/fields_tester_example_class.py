# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields


class BinaryFieldTester(models.TransientModel):
    _name = 'binary_field_improved.binary.field.tester'

    no_name_binary = fields.Binary(u"No name binary", attachment=True)

    default_name_binary = fields.Binary(u"Default name binary", attachment=True)
    default_name_binary_fname = fields.Char(u"Name")

    custom_name_binary = fields.Binary(u"Custom name binary", attachment=True, fname='custom_name')
    custom_name = fields.Char(u"Custom name")
