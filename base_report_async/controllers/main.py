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

from odoo.addons.web.controllers.main import Action, clean_action

from odoo import fields, http
from odoo.http import request


class ActionLoadExtend(Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            # pylint: disable=W0703
            # noinspection PyBroadException
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except Exception:
                action_id = 0  # force failed read

        base_action = request.env['ir.actions.actions'].browse([action_id]).read(['type'])

        if base_action:
            ctx = dict(request.context)
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)
            request.context = ctx
            action = request.env[action_type].browse([action_id]).read()
            if action:
                value = clean_action(action[0])
            active_ids = ctx.get('active_ids', [])
            date_start_for_job_creation = fields.Datetime.now()
            if action_type == 'ir.actions.report' and base_action[0].get('id'):
                report = http.request.env['ir.actions.report'].browse(base_action[0]['id'])
                if report.async_report:
                    if active_ids and len(active_ids) > 100:
                        while active_ids:
                            chunk_active_ids = active_ids[:100]
                            active_ids = active_ids[100:]
                            ctx['active_ids'] = chunk_active_ids
                            running_job_for_user_and_report = report.with_context(ctx). \
                                launch_asynchronous_report_generation(value, date_start_for_job_creation)
                    else:
                        running_job_for_user_and_report = report.with_context(ctx or {}). \
                            launch_asynchronous_report_generation(value, date_start_for_job_creation)
                    return report.notify_user_for_asynchronous_generation(running_job_for_user_and_report)
        return value
