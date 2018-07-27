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

import base64
import re
import zipfile

import os
import json
import time
import zlib

from os.path import basename

import unicodedata
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

from openerp.http import request
from openerp.addons.web.controllers import main
from openerp import http
import tempfile
from openerp.loglevels import ustr


def slugify(string, max_length=None):
    """ Transform a string to a slug that can be used in a url path.

    This method will first try to do the job with python-slugify if present.
    Otherwise it will process string by stripping leading and ending spaces,
    converting unicode chars to ascii, lowering all chars and replacing spaces
    and underscore with hyphen "-".

    :param string: str
    :param max_length: int
    :rtype: str
    """

    string = ustr(string)
    if slugify_lib:
        # There are 2 different libraries only python-slugify is supported
        try:
            return slugify_lib.slugify(string, max_length=max_length)
        except TypeError:
            pass
    uni = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[\W_]', ' ', uni).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)

    return slug[:max_length]


class WebRouteExtend(main.Reports):

    @http.route()
    @main.serialize_exception
    def index(self, action, token):
        current_action = json.loads(action)
        context = dict(request.context)
        context.update(current_action["context"])
        # Normal mode then we call the Odoo methode
        if current_action.get('type_multi_print') == 'zip' and len(context.get('active_ids', [])) > 1:
            return self._zip_report(current_action, token, context)
        if current_action.get('type_multi_print') == 'pdf' and len(context.get('active_ids', [])) > 1:
            return self._pdf_report(current_action, token, context)
        return self._file_report(current_action, token, context)

    def _zip_report(self, current_action, token, context):
        report_srv = request.session.proxy("report")
        report_data, report_ids = self._get_report_data(context, current_action)
        temp_dir = tempfile.mkdtemp()
        num = 0
        for report_id_todo in report_ids:
            report_struct = self._get_report_struct(current_action, report_data, [report_id_todo], report_srv, context)
            report = base64.b64decode(report_struct['result'])
            if report_struct.get('code') == 'zlib':
                report = zlib.decompress(report)

            tmp_file_name = self._get_file_name(current_action, context, [report_id_todo])
            file_name = '%s.%s' % (tmp_file_name, report_struct['format'])

            if os.path.exists("%s/%s" % (temp_dir, file_name)):
                file_name = "%s_%s.%s" % (tmp_file_name, num, report_struct['format'])
                num += 1
            with open("%s/%s" % (temp_dir, file_name), 'wb') as file:
                file.write(report)

        zip_file_name = '%s.zip' % (slugify(current_action.get('name')) or 'documents')
        zip_file_path = '%s/%s' % (temp_dir, zip_file_name)
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            self._zipdir(temp_dir, zipf)

        size = str(os.path.getsize(zip_file_path))
        with open(zip_file_path, 'r') as zf:
            b64zip = zf.read()

        return request.make_response(b64zip, headers=[
            ('Content-Disposition', main.content_disposition(zip_file_name)),
            ('Content-Type', 'application/zip'),
            ('Content-Length', size)],
            cookies={'fileToken': token})

    def _file_report(self, action, token, context):
        report_srv = request.session.proxy("report")

        report_data, report_ids = self._get_report_data(context, action)
        report_struct = self._get_report_struct(action, report_data, report_ids, report_srv, context)
        report = base64.b64decode(report_struct['result'])

        if report_struct.get('code') == 'zlib':
            report = zlib.decompress(report)

        report_mimetype = self.TYPES_MAPPING.get(report_struct['format'], 'octet-stream')
        file_name = '%s.%s' % (self._get_file_name(action, context, report_ids), report_struct['format'])

        return request.make_response(report,
                                     headers=[
                                         ('Content-Disposition', main.content_disposition(file_name)),
                                         ('Content-Type', report_mimetype),
                                         ('Content-Length', len(report))],
                                     cookies={'fileToken': token})

    def _pdf_report(self, action, token, context):
        return self._file_report(action, token, context)

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

    def _zipdir(self, path, ziph):
        # ziph is zipfile handle
        for root, _, files in os.walk(path):
            for file in files:
                if not file.endswith("zip"):
                    file_join = os.path.join(root, file)
                    ziph.write(file_join, basename(file_join))

    def _get_report_struct(self, current_action, report_data, report_id_todo, report_srv, context):
        report_id = report_srv.report(request.session.db, request.session.uid, request.session.password,
                                      current_action["report_name"], report_id_todo,
                                      report_data, context
                                      )
        report_struct = None
        while True:
            report_struct = report_srv.report_get(request.session.db,
                                                  request.session.uid,
                                                  request.session.password,
                                                  report_id)
            if report_struct["state"]:
                break
            time.sleep(self.POLLING_DELAY)

        return report_struct

    def _get_file_name(self, action, context, ids):
        report_obj = request.session.model('ir.actions.report.xml')
        if 'id' in action:
            report = report_obj.read(action['id'], ['name', 'name_eval_report'], context=context)
        else:
            report = report_obj.search([('report_name', '=', action['report_name']), ], context=context)
            report = report_obj.read(report[0], ['name', 'name_eval_report'], context)

        if len(ids) > 1 or len(ids) < 1 or not report['name_eval_report']:
            file_name = report['name']
        else:
            model = request.session.model(context['active_model'])
            file_name = eval(report['name_eval_report'], {'object': model.browse(ids[0]), 'time': time})
        return slugify(file_name)
