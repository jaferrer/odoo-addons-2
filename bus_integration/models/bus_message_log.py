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

from openerp import models, fields


class BusMessageLog(models.Model):
    _name = 'bus.message.log'

    message_id = fields.Many2one('bus.message', string=u"Message")
    type = fields.Selection([('warning', u"Warning"), ('error', u"Error"), ('info', u"Info"),
                             ('processed', u"Processed")], string=u"Log type")
    information = fields.Text(srtring=u"Log information")
    model = fields.Char(u"Model")
    sender_record_id = fields.Integer(u"Sender record id")
    recipient_record_id = fields.Integer(u"Recipient record id")
    external_key = fields.Integer(u"External key")
    recipient_id = fields.Many2one('bus.base', u"Recipient base")
    sender_id = fields.Many2one('bus.base', u"Sender base")
