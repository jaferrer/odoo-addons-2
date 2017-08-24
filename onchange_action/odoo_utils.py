# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from collections import defaultdict
from inspect import getmembers
from openerp import models, api

_logger = logging.getLogger("odoo_utils")


class OnChangeActionModel(models.AbstractModel):
    _name = 'on_change.action'

    @api.multi
    def _action_on_change(self, field_name, field_value):
        return {}

    @api.multi
    def onchange(self, values, field_name, field_onchange):
        res = super(OnChangeActionModel, self).onchange(values, field_name, field_onchange)
        env = self.env

        with env.do_in_onchange():
            def is_onchange_action_id(func):
                return callable(func) and hasattr(func, '_onchange_action_id')

            # If the value is unset then return the value
            if not res.get('value', {}):
                res['value'] = values[field_name]

            for _, func in getmembers(type(self), is_onchange_action_id):
                for name in func._onchange_action_id:
                    # xml id or db id
                    if isinstance(name, (str, basestring, unicode, int)):
                        res['action'] = name
                    else:
                        raise Exception(
                            "You can only use a str, unicode, basestring, "
                            "or an int in the decorator api.onchange_action_id")

            if 'action' not in res:
                self._onchange_action_eval(field_name, result=res)

            if 'action' not in res:
                action_on_change_res = self._action_on_change(field_name, values[field_name])
                if action_on_change_res:
                    # case where the field name is a field in the ir.act.windows too , typically the field 'name'
                    if field_name in action_on_change_res and isinstance(action_on_change_res[field_name], dict):
                        res['action'] = action_on_change_res[field_name]
                    else:
                        res['action'] = action_on_change_res
        return res

    @property
    def _onchange_methods_action(self):
        """ Return a dictionary mapping field names to onchange_action methods. """

        def is_onchange_action(func):
            return callable(func) and hasattr(func, '_onchange_action')

        cls = type(self)
        methods = defaultdict(list)
        for _, func in getmembers(cls, is_onchange_action):
            for name in func._onchange:
                if name not in cls._fields:
                    _logger.warning("@onchange_action%r parameters must be field names", func._onchange_action)
                methods[name].append(func)

        # optimization: memoize result on cls, it will not be recomputed
        cls._onchange_methods_action = methods
        return methods

    def _onchange_action_eval(self, field_name, result):
        """ Apply onchange method(s) for field ``field_name`` with spec ``onchange``
            on record ``self``. Value assignments are applied on ``self``, while
            domain and warning messages are put in dictionary ``result``.
        """
        for method in self._onchange_methods_action.get(field_name, ()):
            method_res = method(self)
            if method_res:
                result['action'] = method_res
