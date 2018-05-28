# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from datetime import datetime

from openerp import addons
from openerp.http import request


class ControllerLoggerContext(addons.web.controllers.main.DataSet):

    def _call_kw(self, model, method, args, kwargs):
        ts = datetime.now()
        res = super(ControllerLoggerContext, self)._call_kw(model, method, args, kwargs)
        uid = request.context.get("uid", 1)
        getattr(request.registry.get('ndp.logging.time'), 'create_record') \
            (request.cr, request.uid, model, method, ts, datetime.now(), uid, "call_button")
        return res
