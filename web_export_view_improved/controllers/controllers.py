# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import datetime
import re
from cStringIO import StringIO
from openerp import fields as OdooFields, api
from openerp.exceptions import UserError
from openerp.tools.misc import xlwt
from openerp.tools.translate import _
from openerp.addons.web.controllers.main import ExcelExport
from openerp.http import request


class ExcelExportViewImproved(ExcelExport):

    def check_is_date(self, value, lang):
        if len(value) == OdooFields.DATE_LENGTH:
            try:
                return datetime.datetime.strptime(value, lang.date_format).date()
            except ValueError:
                return False
        if len(value) == OdooFields.DATETIME_LENGTH:
            try:
                return datetime.datetime.strptime(value, "%s %s" % (lang.date_format, lang.time_format))
            except ValueError:
                return False
        return False

    def from_data(self, fields, rows):
        if len(rows) > 65535:
            raise UserError(_(
                'There are too many rows (%s rows, limit: 65535) to export as Excel 97-2003 (.xls) format. Consider '
                'splitting the export.') % len(rows))
        env = api.Environment(request.cr, request.uid, request.context)
        lang = env['res.lang'].search([('code', '=', env.user.lang)])
        date_format = env['res.lang'].convert_to_xlsx_date(env.user.lang)
        datetime_format = env['res.lang'].convert_to_xlsx_date_time(env.user.lang)
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')

        for i, fieldname in enumerate(fields):
            worksheet.write(0, i, fieldname)
            worksheet.col(i).width = 8000  # around 220 pixels

        base_style = xlwt.easyxf('align: wrap yes')
        date_style = xlwt.easyxf('align: wrap yes', num_format_str=date_format)
        datetime_style = xlwt.easyxf('align: wrap yes', num_format_str=datetime_format)

        for row_index, row in enumerate(rows):
            for cell_index, cell_value in enumerate(row):
                cell_style = base_style
                if isinstance(cell_value, basestring):
                    cell_value = re.sub("\r", " ", cell_value)
                    is_date = self.check_is_date(cell_value, lang)
                    if isinstance(is_date, datetime.datetime):
                        cell_style = datetime_style
                        cell_value = is_date
                    elif isinstance(is_date, datetime.date):
                        cell_style = date_style
                        cell_value = is_date
                elif isinstance(cell_value, datetime.datetime):
                    cell_style = datetime_style
                elif isinstance(cell_value, datetime.date):
                    cell_style = date_style

                worksheet.write(row_index + 1, cell_index, cell_value, cell_style)
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data
