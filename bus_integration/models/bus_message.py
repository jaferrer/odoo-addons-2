#  -*- coding: utf8 -*-

#  -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

#
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
import math

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.addons.connector.queue.job import job
from openerp import models, fields, api
from openerp.addons.connector.session import ConnectorSession
from ..connector.jobs import job_send_response


@job
def job_bus_message_cleaner(session, model_name):
    session.env[model_name].clean_old_messages_async()


@job(default_channel='root.bus_message_cleaner_chunk')
def job_bus_message_cleaner_chunk(session, model_name, message_ids):
    for message in session.env[model_name].browse(message_ids):
        message.unlink()
    return "unlink old bus messages %s: job done." % message_ids


class BusMessage(models.Model):
    """
    messages hierarchy example (sync data from mother to children)
    -------------------------------------------------
    <<lvl I - mother original request>>                     CROSS ID               parent
    -------------------------------------------------
    | -> #1 - SYNC REQUEST                                  master:1
    | <- #2 - DEP REQUEST                                   master:1                  #1
    | -----------------------------------------------
    | <<lvl II - 1st mother dependency response>>
    | -----------------------------------------------
    |   | -> #3 - DEP RESPONSE                              master:1>master:3         #2
    |   | <- #4 - DEP REQUEST                               master:1>master:3         #3
    |   | --------------------------------------------
    |   | <<lvl III - 2nd mother dependency response>>
    |   | --------------------------------------------
    |   |   | -> #5 - DEP RESPONSE                          master:3>master:5         #4
    |   |   | <- #6 - DEP OK                                master:3>master:5         #5          ==> rerun #3
    |   | --------------------------------------------
    |   | <- #7 - DEP OK (from #3)                          master:1>master:3         #3           ==> rerun #1
    | ------------------------------------------------
    | <- #8 - SYNC OK                                       master:1                  #1
    -------------------------------------------------

    messages hierarchy example in case of one2many (sync data from child A  to child B)
        -------------------------------------------------
    <<lvl I - mother original request>>                     CROSS ID               parent
    -------------------------------------------------
    | -> #1 - SYNC REQUEST                                  master:1                            request product.to.send
    | <- #2 - DEP REQUEST                                   master:1                  #1        request production.lot
    | -----------------------------------------------
    | <<lvl II - 1st  dependency response>>
    | -----------------------------------------------
    |   | -> #3 - DEP RESPONSE                              master:1>master:3         #2        send production.lot
    |   | <- #4 - DEP OK                                    master:1>master:3         #3          ==> rerun #1
    |   | --------------------------------------------
    | <- #5 - SYNC OK                                        master:1                 #1
    | -----------------------------------------------
    | <<lvl I - post dependency request>>
    | -----------------------------------------------
    | <- #6 - POST DEP REQUEST   (POST DEPENDENCY)           master:1>master:3         #3        request pedigree.line
    | -----------------------------------------------
    | <<lvl II - post dependency response>>
    | -----------------------------------------------
    |   | -> #7 - DEP RESPONSE                              master:1>master:5         #6        send pedigree line
    |   | <- #8 - DEP OK                                    master:1>master:5         #7        ==> rerun #1
    |   | --------------------------------------------
    | ------------------------------------------------
    | <- #8 - SYNC OK                                       master:1                  #1
    -------------------------------------------------
    """
    _name = 'bus.message'
    _order = 'create_date DESC'

    configuration_id = fields.Many2one('bus.configuration', string=u"Backend")
    batch_id = fields.Many2one('bus.configuration.export', string=u"Batch", index=True)
    job_generate_uuid = fields.Char(u'Generate message job uuid')
    job_send_uuid = fields.Char(u'Send message job uuid')
    export_run_uuid = fields.Char(u'Message group unique identifier',
                                  help='if export is chunked all generated msgs have the same uuid')
    date_done = fields.Datetime(u"Date Done")
    header_param_ids = fields.One2many('bus.message.header.param', 'message_id', u"Header parameters")
    message = fields.Text(u"Message")
    type = fields.Selection([('received', u"Received"), ('sent', u"Sent")], u"Message Type", required=True)
    treatment = fields.Selection([('SYNCHRONIZATION', u"Synchronization request"),
                                  ('DEPENDENCY_SYNCHRONIZATION', u"Dependency response"),
                                  ('DEPENDENCY_DEMAND_SYNCHRONIZATION', u"Dependency request"),
                                  ('POST_DEPENDENCY_DEMAND_SYNCHRONIZATION', u"Post dependency request"),
                                  ('SYNCHRONIZATION_RETURN', u"Synchronization response"),
                                  ('DELETION_SYNCHRONIZATION', u"Deletion request"),
                                  ('DELETION_SYNCHRONIZATION_RETURN', u"Deletion response"),
                                  ('CHECK_SYNCHRONIZATION', u"Check request"),
                                  ('CHECK_SYNCHRONIZATION_RETURN', u"Check response"),
                                  ('BUS_SYNCHRONIZATION', u"bus synchro request"),
                                  ('BUS_SYNCHRONIZATION_RETURN', u"bus synchro response"),
                                  ('RESTRICT_IDS_SYNCHRONIZATION', u"Restrict ID request"),
                                  ('RESTRICT_IDS_SYNCHRONIZATION_RETURN', u"Restrict ID response"),
                                  ], u"Treatment", required=True)
    log_ids = fields.One2many('bus.message.log', 'message_id', string=u"Logs")
    exported_ids = fields.Text(string=u"Exported ids", compute='get_export_eported_ids', store=True)
    message_parent_id = fields.Many2one('bus.message', string=u"Parent message", index=True)
    message_children_ids = fields.One2many('bus.message', 'message_parent_id', string=u"Children messages")

    # enable to identify a message across all the databases (mother/bus/child)
    # to know witch request is targeted by witch response
    cross_id_origin_base = fields.Char("origin base")
    cross_id_origin_id = fields.Integer("origin base message id")
    cross_id_origin_parent_id = fields.Integer("origin base message parent id")

    # computed / related fields
    cross_id_str = fields.Text("cross ID", compute="_compute_cross_id_str", readonly=True)
    body = fields.Text(u"body", compute="_compute_message_fields", readonly=True)
    body_root_pretty_print = fields.Text(u"Body root", compute="_compute_message_fields", readonly=True)
    body_dependencies_pretty_print = fields.Text(u"Body dependencies", compute="_compute_message_fields", readonly=True)
    body_models = fields.Text(u"Models", compute="_compute_message_models", readonly=True, store=True)
    extra_content = fields.Text(u"Extra-content", compute="_compute_message_fields", readonly=True)
    result_state = fields.Selection([('inprogress', u"In progress"), ('error', u"Error"), ('done', u"Done")],
                                    string=u"Result state", default='inprogress', compute='_compute_result_state',
                                    store=True)
    active = fields.Boolean(u'Is active', default=True, index=True)

    @api.multi
    def get_base_origin(self):
        self.ensure_one()
        return self.env['bus.base']\
            .with_context(active_test=False)\
            .search([('bus_username', '=', self.cross_id_origin_base)])

    @api.multi
    def get_json_message(self):
        self.ensure_one()
        return json.loads(self.message, encoding='utf-8')

    @api.multi
    def get_json_dependencies(self):
        self.ensure_one()
        return self.get_json_message().get('body', {}).get('dependency', {})

    @api.multi
    def get_json_post_dependencies(self):
        self.ensure_one()
        return self.get_json_message().get('body', {}).get('post_dependency', {})

    @api.multi
    def deactive(self):
        self.write({'active': False})

    @api.multi
    def reactive(self):
        self.write({'active': True})

    @api.multi
    @api.depends('message')
    def get_export_eported_ids(self):
        for rec in self:
            exported_ids = u""
            if rec.message:
                message_dict = json.loads(rec.message)
                body_dict = message_dict.get('body', {}).get('root', {})
                models = body_dict.keys()
                for model in models:
                    keys = []
                    if isinstance(body_dict.get(model), dict):
                        keys = body_dict.get(model).keys()
                    ids = [int(key) for key in keys]
                    exported_ids += u"%s : %s, " % (model, ids)
            rec.exported_ids = exported_ids

    @api.multi
    def _compute_cross_id_str(self):
        for rec in self:
            if rec.cross_id_origin_parent_id:
                rec.cross_id_str = "%s:%s>%s:%s" % (rec.cross_id_origin_base, rec.cross_id_origin_parent_id,
                                                    rec.cross_id_origin_base, rec.cross_id_origin_id)
            else:
                rec.cross_id_str = "%s:%s" % (rec.cross_id_origin_base, rec.cross_id_origin_id)

    @api.multi
    @api.depends('message')
    def _compute_message_models(self):
        for rec in self:
            try:
                if rec.message:
                    message_dict = json.loads(rec.message)
                    body_dict = message_dict.get('body')
                    if 'demand' in body_dict.keys():
                        models_dict = body_dict.get('demand')
                    elif 'result' in body_dict.get('return', {}).keys():
                        models_dict = body_dict.get('return').get('result')
                    else:
                        models_dict = body_dict.get('root')
                    models_result = []
                    for model in models_dict.keys():
                        models_result.append(str(model))
                    rec.body_models = ', '.join(models_result)
            except ValueError:
                rec.body_models = ""

    @api.multi
    def _compute_message_fields(self):
        for rec in self:
            try:
                message_dict = json.loads(rec.message)
                extra_content_dict = {key: message_dict[key] for key in message_dict if key not in ['body', 'header']}
                rec.extra_content = json.dumps(extra_content_dict)

                body_dict = message_dict.get('body')
                dependencies_dict = body_dict.pop('dependency', {})
                rec.body = json.dumps(body_dict)
                rec.body_root_pretty_print = json.dumps({'body': body_dict}, indent=4)
                rec.body_dependencies_pretty_print = json.dumps({'dependency': dependencies_dict},
                                                                indent=4)
            except ValueError:
                rec.body = rec.message
                rec.body_root_pretty_print = rec.message
                rec.extra_content = ""

    @api.multi
    def name_get(self):
        def to_string(msg):
            return "%s%d" % (u'↗' if msg.type == 'sent' else u'↘', msg.id)

        results = []
        for rec in self:
            treatment_value = dict(self._fields['treatment'].selection).get(rec.treatment)
            result = "%s [%s %s]" % (to_string(rec), treatment_value.lower(), rec.type.upper())
            curr_msg = rec
            while curr_msg.message_parent_id:
                curr_msg = curr_msg.message_parent_id
                result = u"%s %s" % (to_string(curr_msg), result)
            results.append((rec.id, result))
        return results

    @api.model
    def create_message_from_batch(self, message_dict, batch, job_uuid, msgs_group_uuid):
        msg = self.create_message(message_dict, 'sent', batch.configuration_id)
        msg.batch_id = batch.id
        msg.job_generate_uuid = job_uuid
        msg.export_run_uuid = msgs_group_uuid
        return msg

    @api.model
    def create_message(self, message_dict, type_sent_or_received, configuration, parent_message_id=False):
        # message_dict is a JSON loaded dict.
        if not message_dict:
            message_dict = {}
        message = self.create({
            'type': type_sent_or_received,
            'treatment': message_dict.get('header', {}).get('treatment'),
            'configuration_id': configuration.id
        })

        cross_id_origin_base, cross_id_origin_id, cross_id_origin_parent_id = \
            self._explode_cross_origin_base_id_parent(message_dict, configuration.sender_id.bus_username, message.id)

        message_dict['header']['cross_id_origin_base'] = cross_id_origin_base
        message_dict['header']['cross_id_origin_id'] = cross_id_origin_id
        message_dict['header']['cross_id_origin_parent_id'] = cross_id_origin_parent_id

        message.write({
            'message': json.dumps(message_dict),
            'cross_id_origin_base': cross_id_origin_base,
            'cross_id_origin_id': cross_id_origin_id,
            'cross_id_origin_parent_id': cross_id_origin_parent_id,
            'message_parent_id': parent_message_id,
        })

        for key, value in message_dict.get('header', {}).iteritems():
            if key == 'treatment':
                continue
            self.env['bus.message.header.param'].create({
                'message_id': message.id,
                'name': key,
                'value': value,
            })
        return message

    @api.multi
    def _get_first_sent_message(self):
        for rec in self:
            if rec.type == 'sent':
                return rec
        return False

    @api.depends('date_done', 'message')
    def _compute_result_state(self):
        for rec in self:
            if rec.date_done:
                if rec.is_error():
                    rec.result_state = 'error'
                else:
                    rec.result_state = 'done'
            else:
                rec.result_state = 'inprogress'

    @api.multi
    def is_error(self):
        """
        We use a SQL request instead of ORM because of memory issue when too much info logs message ratached to this
        message, also we use LIMIT 1 and retrieve only id because we are only interested in the existence of error
         or not
        """
        self.ensure_one()
        request = """
        SELECT id FROM bus_message_log
        WHERE message_id = %s AND type = 'error'
        LIMIT 1;"""
        self.env.cr.execute(request, (self.id,))
        log_errors = self.env.cr.fetchall()
        state = json.loads(self.message).get('body', {}).get('return', {}).get('state', False)
        return bool(log_errors) or state == "error"

    @api.multi
    def add_log(self, message, log_type='info'):
        """
        Add a log to the message
        set the message state to done when an error log is passed.
        :param message: log message..
        :param log_type: info|warning|error|processed
        """
        self.ensure_one()
        log = self.env['bus.message.log'].create({
            'message_id': self.id,
            'type': log_type,
            'information': message
        })
        # needed to change message state to done..
        if log_type == 'error':
            self.date_done = fields.Datetime.now()
        return log

    @api.model
    def _explode_cross_origin_base_id_parent(self, message_dict, default_base=False, default_msg_id=False):
        header_dict = message_dict.get('header', {})
        base = header_dict.get('cross_id_origin_base', default_base)
        msg_id = header_dict.get('cross_id_origin_id', default_msg_id)
        msg_parent_id = header_dict.get('cross_id_origin_parent_id', False)
        return base, msg_id, msg_parent_id

    @api.model
    def get_parent_cross_id_messages(self, message_dict):
        """
        search for the last sent message of the parent level
        :param message_dict:
        :return: the parent message or False
        """
        origin_base, _, origin_parent_id = self._explode_cross_origin_base_id_parent(message_dict)
        return self.env['bus.message'].search([('cross_id_origin_base', '=', origin_base),
                                               ('cross_id_origin_id', '=', origin_parent_id),
                                               ('type', '=', 'sent')], order='id desc')

    @api.model
    def get_same_cross_id_messages(self, message_dict):
        """
        :return: messages with the same cross id (origin, parent_id and id)
        """
        origin_base, origin_id, origin_parent_id = self._explode_cross_origin_base_id_parent(message_dict)
        domain = [('cross_id_origin_base', '=', origin_base),
                  ('cross_id_origin_id', '=', origin_id)]
        if origin_parent_id:
            domain.append(('cross_id_origin_parent_id', '=', origin_parent_id))
        return self.search(domain, order='id desc')

    @api.multi
    def get_parent(self):
        """
        :param message: received or sent message to find parent's received/sent message
        :return: messages with the same cross id (origin, parent_id and id) without the message param
        """
        self.ensure_one()
        if not self.cross_id_origin_parent_id:
            return False
        return self.search([('cross_id_origin_base', '=', self.cross_id_origin_base),
                            ('cross_id_origin_id', '=', self.cross_id_origin_parent_id),
                            ('type', '=', self.type)], order='id desc', limit=1)

    @api.multi
    def send(self, msg_content_dict):
        self.ensure_one()
        self.job_send_uuid = job_send_response.delay(ConnectorSession.from_env(self.env), 'bus.configuration',
                                                     self.configuration_id.id, json.dumps(msg_content_dict))
        return self.job_send_uuid

    @api.model
    def clean_old_messages_async(self):
        keep_messages_for = self.env.ref('bus_integration.backend').keep_messages_for
        if not keep_messages_for:
            return
        limit_date = datetime.now() - relativedelta(days=keep_messages_for)
        old_msgs = self.search([('create_date', '<', fields.Datetime.to_string(limit_date))])
        chunk_size = 100
        cpt = 0
        max = int(math.ceil(len(old_msgs) / float(chunk_size)))
        while old_msgs:
            cpt += 1
            chunk = old_msgs[:chunk_size]
            old_msgs = old_msgs[chunk_size:]
            session = ConnectorSession(self.env.cr, self.env.uid, self.env.context)
            job_bus_message_cleaner_chunk.delay(session, 'bus.message', chunk.ids,
                                                description="bus message cleaner (chunk %s/%s)" % (cpt, max))

    @api.model
    def cron_bus_message_cleaner(self):
        job_bus_message_cleaner.delay(ConnectorSession.from_env(self.env), 'bus.message',
                                      description=u"bus message cleaner - remove old messages.")


class BusMessageHearderParam(models.Model):
    _name = 'bus.message.header.param'

    message_id = fields.Many2one('bus.message', u"Message", required=True, ondelete='cascade', index=True)
    name = fields.Char(u"Key", required=True)
    value = fields.Char(u"Value")
