

from odoo import http, exceptions
from odoo.http import request
from odoo.tools import safe_eval
from openerp.addons.web.controllers import main


class Action(main.Action):

    @http.route()
    def load(self, action_id, additional_context=None):
        res = super(Action, self).load(action_id, additional_context)
        model_actions = request.env['ir.actions.actions']
        try:
            action_id = int(action_id)
        except ValueError:
            try:
                action = request.env.ref(action_id)
                assert action._name.startswith('ir.actions.')
                action_id = action.id
            except exceptions.ValidationError:
                action_id = 0   # force failed read
        base_action = model_actions.browse([action_id]).read([])[0]
        ctx = dict(request.context)
        if base_action.get('propagate_context', False) or ctx.get('propagate_context', False):
            action_ctx = safe_eval(res.get('context', '{}'))
            action_ctx.update(ctx)
            res['context'] = str(action_ctx)
        return res
