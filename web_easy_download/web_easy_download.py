# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo.http import request

from odoo import http


class Binary(http.Controller):

    @http.route('/web/binary/saveas', type='http', auth="public")
    # @serialize_exception
    def saveas(self, model, field, id=None, filename_field=None, **kw):
        """ Download link for files stored as binary fields.

        If the ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename_field: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        model_env = request.env[model]
        fields = [field]
        record = model_env.browse(int(id))
        if filename_field:
            fields.append(filename_field)
        if id:
            res = record.read()[0]
        else:
            res = model_env.default_get(fields)
        filecontent = base64.b64decode(res.get(field) or '')
        if not filecontent:
            return request.not_found()
        else:
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if filename_field:
                filename = res.get(filename_field, '') or filename
            return request.make_response(filecontent,
                                         [('Content-Type', 'application/octet-stream'),
                                          ('Content-Disposition', http.content_disposition(filename))])
