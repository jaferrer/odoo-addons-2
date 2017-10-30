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

from openerp import models, api
from openerp.report import interface
from openerp.report.report_sxw import rml_parse
from . import aeroo_extend_delete_old


class IrActionAeroo(models.Model):
    _inherit = 'ir.actions.report.xml'

    @api.model
    def register_report(self, name, model, tmpl_path, parser):
        record = self.env['ir.actions.report.xml'].search([('report_name', '=', name)]).read(['id', 'delete_old'])[0]
        if record['delete_old']:
            res = aeroo_extend_delete_old.ExtendAerooReport(self.env.cr, 'report.%s' % name, model, tmpl_path, parser)
        else:
            res = super(IrActionAeroo, self).register_report(name, model, tmpl_path, parser)
        return res

    @api.cr
    def _lookup_report(self, cr, name):
        if 'report.' + name in interface.report_int._reports:
            new_report = interface.report_int._reports['report.' + name]
        else:
            cr.execute("SELECT id, active, report_type, parser_state, \
                            parser_loc, parser_def, model, report_rml \
                            FROM ir_act_report_xml \
                            WHERE report_name=%s", (name,))
            record = cr.dictfetchone()
            if record['report_type'] == 'aeroo':
                if record['active'] == True:
                    parser = rml_parse
                    if record['parser_state'] == 'loc' and record['parser_loc']:
                        parser = self.load_from_file(cr, 1, record['parser_loc'], record['id']) or parser
                    elif record['parser_state'] == 'def' and record['parser_def']:
                        parser = self.load_from_source(cr, 1, record['parser_def']) or parser
                    new_report = self.register_report(cr, 1, name, record['model'], record['report_rml'], parser)
                else:
                    new_report = False
            else:
                new_report = super(IrActionAeroo, self)._lookup_report(cr, name)
        return new_report
