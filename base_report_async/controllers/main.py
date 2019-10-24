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

from openerp.addons.web.controllers.main import clean_action, Action

from openerp import http
from openerp.http import request


class ActionLoadExtend(Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, do_not_eval=False, additional_context=None):
        Actions = request.session.model('ir.actions.actions')
        value = False
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                module, xmlid = action_id.split('.', 1)
                model, action_id = request.session.model('ir.model.data').get_object_reference(module, xmlid)
                assert model.startswith('ir.actions.')
            except Exception:
                action_id = 0  # force failed read

        base_action = Actions.read([action_id], ['type'], request.context)

        if base_action:
            ctx = request.context
            action_type = base_action[0]['type']
            if action_type == 'ir.actions.report.xml':
                ctx.update({'bin_size': True})
            if additional_context:
                ctx.update(additional_context)

            action = request.session.model(action_type).read([action_id], False, ctx)
            if action:
                value = clean_action(action[0])
            if action_type == 'ir.actions.report.xml' and base_action[0].get('id'):
                report = request.session.model('ir.actions.report.xml').browse(base_action[0]['id'])
                if report.async_report:
                    running_job_for_user_and_report = report.with_context(ctx or {}). \
                        launch_asynchronous_report_generation(value)
                    return report.notify_user_for_asynchronous_generation(running_job_for_user_and_report)
        return value
