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

import json

from openerp import models, fields, api


class BusMessage(models.Model):
    _name = 'bus.message'

    id_serial = fields.Char(string=u"Serial ID")
    backend_id = fields.Many2one('bus.backend', string=u"Backend")
    done = fields.Boolean(u"Done")
    date_done = fields.Datetime(u"Date Done")
    header_param_ids = fields.One2many('bus.message.header.param', 'message_id', u"Header parameters")
    body = fields.Text(u"Body")
    extra_content = fields.Text(u"Extra-content")
    message = fields.Text(u"Message")
    type = fields.Selection([('received', u"Received"), ('sent', u"Sent")], u"Message Type", required=True)
    treatment = fields.Selection([('SYNCHRONIZATION', u"Synchronization"),
                                  ('DEPENDENCY_SYNCHRONIZATION', u"Dependency synchronization"),
                                  ('DEPENDENCY_DEMAND_SYNCHRONIZATION', u"Dependency demand sychronization"),
                                  ('SYNCHRONIZATION_RETURN', u"Synchronization return"),
                                  ('DELETION_SYNCHRONIZATION', u"Deletion synchronization"),
                                  ('DELETION_SYNCHRONIZATION_RETURN', u"Deletion synchronization return"),
                                  ], u"Treatment", required=True)
    state = fields.Selection([('reception', u"Recetion"), ('send', u"Send"), ('error', u"Error"),
                              ('warning', u"Warning")], string=u"State")
    log_ids = fields.One2many('bus.message.log', 'message_id', string=u"Logs")

    @api.multi
    def name_get(self):
        return [(rec.id, u"Message %s on %s" % (rec.type, rec.create_date)) for rec in self]

    @api.model
    def create_message(self, message_dict=None, type='', backend_id=0):
        # message_dict is a JSON loaded dict.
        if not message_dict:
            message_dict = {}
        extra_content_dict = {key: message_dict[key] for key in message_dict if key not in ['body', 'header']}
        message = self.create({
            'body': message_dict.get('body', """"""),
            'message': json.dumps(message_dict, indent=4),
            'extra_content': extra_content_dict and json.dumps(extra_content_dict, indent=4) or """""",
            'type': type,
            'treatment': message_dict.get('header', {}).get('treatment'),
            'id_serial': message_dict.get('header', {}).get('serial_id'),
            'backend_id': backend_id
        })
        for key, value in message_dict.get('header', {}).iteritems():
            if key == 'treatment' or key == 'serial_id':
                continue
            self.env['bus.message.header.param'].create({
                'message_id': message.id,
                'name': key,
                'value': value,
            })
        return message

    @api.model
    def create(self, vals):
        if vals.get('done'):
            vals['date_done'] = fields.Datetime.now()
        return super(BusMessage, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('done'):
            vals['date_done'] = fields.Datetime.now()
        return super(BusMessage, self).write(vals)


class BusMessageHearderParam(models.Model):
    _name = 'bus.message.header.param'

    message_id = fields.Many2one('bus.message', u"Message", required=True)
    name = fields.Char(u"Key", required=True)
    value = fields.Char(u"Value")
