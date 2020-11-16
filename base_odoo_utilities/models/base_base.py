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

from odoo import models, api


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    def first(self, func_filter=None):
        """Methode sans @api.multi ou model car compatible pour les deux
        Renvoi le premier element de self si plusieurs `ids` sinon renvoie self"""
        if not func_filter:
            return self and self[0] or self
        if isinstance(func_filter, str):
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
        if isinstance(func_filter, str):
            func_filter = getattr(self, func_filter)
        for rec in reversed(self):
            if func_filter(rec):
                return rec
        return self.env[self._name]

    @api.multi
    def save_and_close(self):
        return {'type': 'ir.actions.act_window_close'}
