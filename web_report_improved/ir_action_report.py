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

from openerp import models, fields, api


class IrAction(models.Model):
    _inherit = 'ir.actions.report.xml'

    type_multi_print = fields.Selection((
        ('file', u"Unique File"),
        ('pdf', u"Merged Pdf"),
        ('zip', u"Zip Container")
    ), u"Type container", default='file')

    name_eval_report = fields.Char(u"Expression for the name of the report")


class Report(models.Model):
    _inherit = 'report'

    @api.v7
    def get_action(self, cr, uid, ids, report_name, data=None, context=None):
        result = super(Report, self).get_action(cr, uid, ids, report_name, data=data, context=context)
        report_xml_id = self.pool.get('ir.actions.report.xml'). \
            search(cr, uid, [('report_name', '=', report_name),
                             ('model', '=', context.get('active_model'))], context=context)
        report_xml = self.pool.get('ir.actions.report.xml').browse(cr, uid, report_xml_id, context=context)
        if report_xml:
            result['name'] = report_xml.name
            result['type_multi_print'] = report_xml.type_multi_print
            result['name_eval_report'] = report_xml.name_eval_report
        return result

    @api.v8
    def get_action(self, records, report_name, data=None):
        ctx = self._context.copy()
        ctx['active_model'] = records._name
        return Report.get_action(self._model, self._cr, self._uid, records.ids, report_name, data=data, context=ctx)
