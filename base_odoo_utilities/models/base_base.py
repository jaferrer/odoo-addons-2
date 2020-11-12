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

from odoo import models, api, tools


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    def first(self, func_filter=None):
        """Methode sans @api.multi ou model car compatible pour les deux
        Renvoi le premier element de self si plusieurs `ids` sinon renvoie self"""
        if not func_filter:
            return self and self[0] or self
        if isinstance(func_filter, (unicode, str)):
            func_filter = getattr(self, func_filter)
        for rec in self:
            if func_filter(rec):
                return rec
        return self.env[self._name]

    def last(self, func_filter=None):
        """Methode sans @api.multi ou model car compatible pour les deux
        Renvoi le dernier element de self si plusieurs `ids` sinon renvoie self"""
        if not func_filter:
            return self and self[-1] or self
        if isinstance(func_filter, (unicode, str)):
            func_filter = getattr(self, func_filter)
        for rec in reversed(self):
            if func_filter(rec):
                return rec
        return self.env[self._name]

    @api.multi
    def save_and_close(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _get_selection_label(self, field='state', lang=None):
        """
        Return the selection field value translated
        :param field: by default 'state' because 99% this the wanted state, must be a fields.Selection
        :param lang: the wanted language, if not set we get it in the context or in last case in the current user
        :return The translated value of the field value in self
        """
        self.ensure_one()
        selection_dict = dict(self._fields[field].selection).get(self[field])
        lang = lang or self.env.context.get('lang', self.env.user.lang)
        return self.env['ir.translation']._get_source(None, 'selection', lang, selection_dict)

    @api.model
    def _get_selection_label_translated(self, field='state', lang=None):
        """
        :param field: by default 'state' because 99% this the wanted state, must be a fields.Selection
        :param lang: the wanted language, if not set we get it in the context or in last case in the current user
        :return a dict with for each state the translated term
        """
        result = {}
        lang = lang or self.env.context.get('lang', self.env.user.lang)
        for key, value in dict(self._fields[field].selection).items():
            result[key] = self.env['ir.translation']._get_source(None, 'selection', lang, value)
        return result

    @api.model
    def float_to_time_str(self, time_float, in_utc=False):
        """
        Convert a float to time format like the widget 'float_time' in view
        Ex:
        >>> float_to_time(0.5) == "00:30"
        >>> float_to_time(1.25) == "01:15"

        :param time_float: the float to convert
        :return: return the float as HH:mm format
        """
        if in_utc:
            now = datetime.now()
            hour, minute = divmod(time_float * 60, 60)
            dt = now.replace(hour=int(hour), minute=int(minute))
            dt = self.env.user.utcize_date(dt)
            return dt.strftime(tools.DEFAULT_SERVER_TIME_FORMAT)
        return '{0:02.0f}:{1:02.0f}'.format(*divmod(time_float * 60, 60))
