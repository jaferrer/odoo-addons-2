from openerp import http, tools
import simplejson
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO
from collections import deque
from openerp.tools.misc import find_in_path
import base64
from datetime import datetime


class WebCalendarExporter(http.Controller):

    @http.route('/web_calendar_export/export_calendar', type='http', auth="user")
    def export_calendar(self, data, token):
        data = base64.decodestring(data)

        contenthtml = u"""<html><head>
        <link type="text/css" href="/website/static/src/less/web.assets_backend/import_bootstrap.less.css"  rel="stylesheet">
        <link type="text/css" href="/web_calendar/static/src/less/web.assets_backend/web_calendar.less.css"  rel="stylesheet">
        <link type="text/css" href="/web_calendar/static/lib/fullcalendar/css/fullcalendar.css" rel="stylesheet">
        <head><body style="width:100%%;height:100%%;padding-right:10px;">
            %s
            </body></html>"""

        contenthtml = contenthtml % (tools.ustr(
            data))

        base_url = request.env["ir.config_parameter"].get_param(
            'report.url') or request.env["ir.config_parameter"].get_param('web.base.url')

        mini_template = request.env.ref('report.minimal_layout')

        node = mini_template.render(dict(subst=True, body=contenthtml, base_url=base_url))

        paperformat = request.env.user.company_id.paperformat_id
        paperformat.margin_top = 5
        paperformat.margin_bottom = 5
        paperformat.margin_left = 0
        paperformat.margin_right = 0
        spec_paperformat_args = {}

        index = node.find('</head>')

        node = (tools.ustr(
            node[:index]) + u"""<meta http-equiv="content-type" content="text/html; charset=UTF-8"/>""" + tools.ustr(node[index:])).encode("utf-8")

        content = request.env["report"]._run_wkhtmltopdf(
            None, None, [(0, node)], True, paperformat, spec_paperformat_args=spec_paperformat_args, save_in_attachment={})

        response = request.make_response(content,
                                         headers=[('Content-Type', 'application/pdf'),
                                                  ('Content-Disposition', 'attachment; filename=export.pdf;')],
                                         cookies={'fileToken': token})
        return response
