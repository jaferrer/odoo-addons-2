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

from odoo.addons.web.controllers.main import Action

from odoo import fields, http
from odoo.http import request


class ActionLoadExtend(Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        action = super(ActionLoadExtend, self).load(action_id, additional_context)
        if action.get('type') != 'ir.actions.report':
            return action
        report = http.request.env['ir.actions.report'].browse(action['id'])
        if not report.async_report:
            return action
        running_job_for_user_and_report = False
        ctx = dict(request.context)
        active_ids = ctx.get('active_ids', [])
        if active_ids and len(active_ids) > 100:
            while active_ids:
                chunk_active_ids = active_ids[:100]
                active_ids = active_ids[100:]
                ctx['active_ids'] = chunk_active_ids
                running_job_for_user_and_report = report.with_context(ctx). \
                    launch_asynchronous_report_generation(action, fields.Datetime.now())
        else:
            running_job_for_user_and_report = report.with_context(ctx or {}). \
                launch_asynchronous_report_generation(action, fields.Datetime.now())
        return report.notify_user_for_asynchronous_generation(running_job_for_user_and_report)
