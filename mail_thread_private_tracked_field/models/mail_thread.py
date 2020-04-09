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

from odoo import models, api

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _track_subtype(self, init_values):
        if 'force_subtype_xmlid' in self.env.context:
            res = self.env.context['force_subtype_xmlid']
        else:
            res = super(MailThread, self)._track_subtype(init_values)
        return res

    @api.multi
    def message_track(self, tracked_fields, initial_values):
        private_field_names = []
        for name, field in self._fields.items():
            if getattr(field, 'track_visibility_internal_only', False):
                private_field_names += [name]
        private_tracked_fields = {field_name: tracked_fields[field_name] for field_name in tracked_fields if
                                  field_name in private_field_names}
        public_tracked_fields = {field_name: tracked_fields[field_name] for field_name in tracked_fields if
                                 field_name not in private_field_names}
        if public_tracked_fields:
            if 'force_subtype_xmlid' not in self.env.context:
                super(MailThread, self.with_context(force_subtype_xmlid='mail.mt_comment')). \
                    message_track(public_tracked_fields, initial_values)
            else:
                super(MailThread, self).message_track(public_tracked_fields, initial_values)
        if private_tracked_fields:
            super(MailThread, self.with_context(force_subtype_xmlid='mail.mt_note')). \
                message_track(private_tracked_fields, initial_values)
        return True
