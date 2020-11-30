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


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def check_mail_message_access(self, res_ids, operation, model_name=None):
        if model_name:
            doc_model = self.env[model_name]
        else:
            doc_model = self

        custom_check_method = getattr(doc_model, 'custom_check_mail_message_access', None)
        if callable(custom_check_method):
            return custom_check_method()

        return super(MailThread, self).check_mail_message_access(res_ids, operation, model_name)
