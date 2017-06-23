# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.addons.report_aeroo.report_aeroo import Aeroo_report

def delete_old_report(cr, uid, ids, table, context):
    pool = openerp.registry(cr.dbname)
    aids = pool.get('ir.attachment').search(cr, uid, [('res_id', 'in', ids), ('res_model', '=', table)])
    pool.get('ir.attachment').unlink(cr, uid, aids, context)


class ExtendAerooReport(Aeroo_report):

    def create_source_pdf(self, cr, uid, ids, data, report_xml, context=None):
        context = context or {}
        context['aeroo_docs'] = self.aeroo_docs_enabled(cr)
        if report_xml.delete_old and (report_xml.attachment_use or context.get('attachment_use', True)):
            delete_old_report(cr, uid, ids, self.table, context)
        return super(ExtendAerooReport, self).create_source_pdf(cr, uid, ids, data, report_xml, context)

    def create_source_odt(self, cr, uid, ids, data, report_xml, context=None):
        context = context or {}
        context['aeroo_docs'] = self.aeroo_docs_enabled(cr)
        if report_xml.delete_old and not (report_xml.attachment_use and context.get('attachment_use', True)):
            delete_old_report(cr, uid, ids, self.table, context)
        return super(ExtendAerooReport, self).create_source_odt(cr, uid, ids, data, report_xml, context)
