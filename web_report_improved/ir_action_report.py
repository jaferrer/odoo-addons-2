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
import os

import operator
import openerp
from openerp import models, fields
from openerp.report.report_sxw import report_rml
from . import swx_extend_delete_old


class IrAction(models.Model):
    _inherit = 'ir.actions.report.xml'

    type_multi_print = fields.Selection((
        ('file', u"Unique File"),
        ('pdf', u"Merged Pdf"),
        ('zip', u"Zip Container")
    ), u"Type container", default='file')

    name_eval_report = fields.Char(u"Expression for the name of the report")

    delete_old = fields.Boolean(u"Delete history")

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        opj = os.path.join
        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser sepcified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s", (name,))
            dict_report = cr.dictfetchone()
            if dict_report:
                if dict_report['report_type'] in ['qweb-pdf', 'qweb-html']:
                    return dict_report['report_name']
                elif dict_report['report_rml'] or dict_report['report_rml_content_data']:
                    if dict_report['parser']:
                        kwargs = {'parser': operator.attrgetter(dict_report['parser'])(openerp.addons)}
                    else:
                        kwargs = {}
                    new_report = swx_extend_delete_old.ExtendSwxReport(
                        'report.' + dict_report['report_name'], dict_report['model'],
                        opj('addons', dict_report['report_rml'] or '/'),
                        header=dict_report['header'], register=False, **kwargs)
                elif dict_report['report_xsl'] and dict_report['report_xml']:
                    new_report = report_rml('report.' + dict_report['report_name'], dict_report['model'],
                                            opj('addons', dict_report['report_xml']),
                                            dict_report['report_xsl'] and opj('addons', dict_report['report_xsl']),
                                            register=False)
                else:
                    new_report = super(IrAction, self)._lookup_report(cr, name)
                    if not new_report:
                        raise "Unhandled report type: %s" % dict_report
            else:
                raise "Required report does not exist: %s" % name

        return new_report
