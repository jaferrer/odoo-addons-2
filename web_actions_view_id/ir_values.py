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
import logging

from openerp import models, fields, api, http, addons

_logger = logging.getLogger(__name__)


class ControlerViewIdInContext(addons.web.controllers.main.DataSet):

    @http.route()
    def call_kw(self, model, method, args, kwargs, path=None):
        if method == "fields_view_get":
            if "view_type" in kwargs and "context" in kwargs and "view_type_fields_view_get" not in kwargs["context"]:
                kwargs["context"]["view_type_fields_view_get"] = kwargs["view_type"]
            if "view_id" in kwargs and "context" in kwargs and "view_id_fields_view_get" not in kwargs["context"]:
                kwargs["context"]["view_id_fields_view_get"] = kwargs["view_id"]
        return super(ControlerViewIdInContext, self).call_kw(model, method, args, kwargs, path)


class IrValues(models.Model):
    _inherit = 'ir.values'

    @api.model
    def get_actions(self, action_slot, model, res_id=False):
        res = super(IrValues, self).get_actions(action_slot, model, res_id)
        action = self.env.context.get("params", {}).get("action")
        view_id = None
        if action and self.env.context.get("view_type_fields_view_get"):
            view_id = self.find_view_id(model)
        filtered_result = []
        for id, name, action_def in res:
            view_ids = action_def.get('view_ids', [])
            if not view_ids or view_id in view_ids:
                filtered_result.append((id, name, action_def))
        return filtered_result

    @api.model
    def find_view_id(self, model_name):
        # try to find a view_id if none provided
        View = self.env['ir.ui.view']
        view_id = self.env.context.get("view_id_fields_view_get")
        if not view_id:
            # <view_type>_view_ref in context can be used to overrride the default view
            view_type = self.env.context.get("view_type_fields_view_get")
            view_ref_key = view_type + '_view_ref'
            view_ref = self.env.context.get(view_ref_key)
            if view_ref:
                if '.' in view_ref:
                    module, view_ref = view_ref.split('.', 1)
                    self.env.cr.execute("""SELECT res_id
FROM ir_model_data
WHERE model = 'ir.ui.view' AND module = %s AND name = %s""", (module, view_ref))
                    view_ref_res = self.env.cr.fetchone()
                    if view_ref_res:
                        view_id = view_ref_res[0]
                else:
                    _logger.warning('%r requires a fully-qualified external id (got: %r for model %s). '
                                    'Please use the complete `module.view_id` form instead.', view_ref_key, view_ref,
                                    model_name)

            if not view_id:
                # otherwise try to find the lowest priority matching ir.ui.view
                view_id = View.default_view(model_name, view_type)
        return view_id


class ActServer(models.Model):
    _inherit = 'ir.actions.server'

    view_ids = fields.Many2many('ir.ui.view', string=u"Views")
