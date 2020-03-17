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

    message_id = fields.Many2one('bus.message', string=u"Message", ondelete='cascade', index=True, required=True)
    type = fields.Selection([('warning', u"Warning"), ('error', u"Error"), ('info', u"Info"),
                             ('processed', u"Processed")], string=u"Log type", index=True)
    information = fields.Text(srtring=u"Log information")
    model = fields.Char(u"Model", index=True)
    sender_record_id = fields.Integer(u"Sender record id", index=True)
    recipient_record_id = fields.Integer(u"Recipient record id", index=True)
    external_key = fields.Integer(u"External key", index=True)
    recipient_id = fields.Many2one('bus.base', u"Recipient base", index=True)
    sender_id = fields.Many2one('bus.base', u"Sender base", index=True)
