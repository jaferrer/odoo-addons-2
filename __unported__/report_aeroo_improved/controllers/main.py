# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import base64
import zlib
import time

from openerp.addons.web.http import Controller, route, request
from openerp.addons.web.controllers.main import Reports
from openerp.http import content_disposition
from openerp.addons.report.controllers.main import ReportController
from openerp.exceptions import UserError



class ReportAerooController(ReportController):

    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------

    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        """Add the 'aeroo' converter"""
        if converter != "aeroo":
            return super(ReportAerooController, self).report_routes(reportname, docids, converter, **data)

        if docids:
            docids = [int(i) for i in docids.split(',')]

        context = dict(request.context)

        report = request.env['ir.actions.report.xml'].search([('report_name', '=', reportname)])
        if not report:
            raise UserError("Bad Report Reference" + "This report is not loaded into the database: %s." % reportname)

        context.update({
            'active_model': report.model
        })
        action = {
            'context': context,
            'data': data,
            'type': 'ir.actions.report.xml',
            'report_name': report.report_name,
            'report_type': report.report_type,
            'report_file': report.report_file,
        }

        report_srv = request.session.proxy("report")
        report_data, _ = self._get_report_data(context, action)
        report_struct = self._get_report_struct(action, report_data, docids, report_srv, context)
        report = base64.b64decode(report_struct['result'])

        if report_struct.get('code') == 'zlib':
            report = zlib.decompress(report)

        report_mimetype = Reports.TYPES_MAPPING.get(report_struct['format'], 'octet-stream')
        file_name = '%s.%s' % (reportname, report_struct['format'])

        return request.make_response(report,
                                     headers=[
                                         ('Content-Disposition', content_disposition(file_name)),
                                         ('Content-Type', report_mimetype),
                                         ('Content-Length', len(report))
                                     ])

    def _get_report_data(self, context, current_action):
        report_data = {}
        report_ids = context.get("active_ids", None)
        if 'report_type' in current_action:
            report_data['report_type'] = current_action['report_type']
        if 'datas' in current_action:
            if 'ids' in current_action['datas']:
                report_ids = current_action['datas'].pop('ids')
            report_data.update(current_action['datas'])
        return report_data, report_ids

    def _get_report_struct(self, current_action, report_data, report_id_todo, report_srv, context):
        report_id = report_srv.report(request.session.db, request.session.uid, request.session.password,
                                      current_action["report_name"], report_id_todo,
                                      report_data, context
                                      )
        while True:
            report_struct = report_srv.report_get(request.session.db,
                                                  request.session.uid,
                                                  request.session.password,
                                                  report_id)
            if report_struct["state"]:
                break
            time.sleep(Reports.POLLING_DELAY)

        return report_struct
