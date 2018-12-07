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
from openerp import models, api


class ResLang(models.Model):
    _inherit = 'res.lang'

    _dict_python_date_to_xlsx = {
        "%Y": "yyyy",
        "%m": "mm",
        "%d": "dd",
        "%H": "hh",
        "%M": "mm",
        "%S": "ss",
    }

    @api.model
    def convert_to_xlsx_date(self, lang_code):
        lang = self.search([('code', '=', lang_code)])
        xlsx_format = lang.date_format
        for py_type, xlsx_type in self._dict_python_date_to_xlsx.items():
            xlsx_format = xlsx_format.replace(py_type, xlsx_type)
        return xlsx_format

    @api.model
    def convert_to_xlsx_date_time(self, lang_code):
        lang = self.search([('code', '=', lang_code)])
        xlsx_format = "%s %s" % (lang.date_format, lang.time_format)
        for py_type, xlsx_type in self._dict_python_date_to_xlsx.items():
            xlsx_format = xlsx_format.replace(py_type, xlsx_format)
        return xlsx_format
