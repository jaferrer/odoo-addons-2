# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BarcodeController(http.Controller):

    @http.route(['/web_ui_stock/web/'], type='http', auth='user')
    def web_ui_stock_route(self, debug=False, **kwargs):
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=/barcode_stock/web')
        return request.render('web_ui_stock.index', qcontext=kwargs)
