# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo.addons.queue_job.job import job

from odoo import models, api, fields, exceptions

_logger = logging.getLogger(__name__)


class ResendMailsLimitedNumber(models.Model):
    _inherit = 'mail.mail'

    nb_automatic_resend = fields.Integer(u"Number of automatic resend", readonly=True)

    @job
    @api.multi
    def resend_failed_mails_limited_number(self):
        max_nb_resend_before_raise = int(self.env['ir.config_parameter'].
                                         get_param('auto_resend_email_limited_number.max_nb_resend_before_raise'))
        if not max_nb_resend_before_raise:
            return
        for rec in self:
            rec.nb_automatic_resend = rec.nb_automatic_resend + 1
            rec.state = 'outgoing'
            rec.send()
            if rec.state == 'exception' and rec.nb_automatic_resend >= max_nb_resend_before_raise:
                raise exceptions.UserError(u"Mail with ID=%s has been resend more than %s times with no success" %
                                           (rec.id, max_nb_resend_before_raise))

    @api.multi
    def resend_failed_mails(self):
        mail_failed_list = self.env['mail.mail'].search([('state', '=', 'exception')])
        nb_failed_mails = len(mail_failed_list)
        index = 0
        for failed_mail in mail_failed_list:
            index += 1
            _logger.info(u"Generating job to relaunch mail with ID=%s (%s/%s)", failed_mail.id, index, nb_failed_mails)
            failed_mail.with_delay().resend_failed_mails_limited_number()
