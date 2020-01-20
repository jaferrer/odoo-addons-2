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
from openerp import models, api


class Mail(models.Model):
    """
    adds [ribbon name] prefix to mail's objects if set or does nothing.
    """
    _inherit = 'mail.mail'

    @api.multi
    def insert_subject_prefix(self, vals):
        if 'subject' not in vals:
            return vals
        ribbon_name = self.env['web.environment.ribbon.backend']._prepare_ribbon_name()
        if ribbon_name == "False":
            return vals

        prefix = "[%s] - " % ribbon_name.lower()
        if prefix not in vals['subject']:
            vals['subject'] = "%s%s" % (prefix, vals['subject'])

        return True

    @api.model
    def create(self, vals):
        self.insert_subject_prefix(vals)
        return super(Mail, self).create(vals)

    @api.multi
    def write(self, vals):
        self.insert_subject_prefix(vals)
        return super(Mail, self).write(vals)
