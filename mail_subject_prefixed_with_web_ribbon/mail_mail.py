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
    _inherit = 'mail.mail'

    @api.model
    def send_get_mail_subject(self, mail, force=False, partner=None):
        """ prefix mail subject to identify odoo instance """
        subject = super(Mail, self).send_get_mail_subject(mail, force, partner)
        ribbon_name = self.env['ir.config_parameter'].get_param('ribbon.name', "False")
        odoo_instance_identifier = "" if ribbon_name == "False" else ribbon_name
        if not odoo_instance_identifier:
            return subject

        base_tag_prefix = "[%s] - " % odoo_instance_identifier.lower()
        if base_tag_prefix not in subject:
            subject = "%s%s" % (base_tag_prefix, subject)

        return subject
