# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from datetime import datetime
from dateutil import relativedelta

from openerp import models, fields, api
from openerp.addons.connector.session import ConnectorSession
from openerp.tools import safe_eval
from ..connector.jobs import job_generate_message


class BusextendBackendBatch(models.Model):
    _name = 'bus.backend.batch'

    name = fields.Char(u"Name", required=True)
    backend_id = fields.Many2one('bus.backend', string=u"Backend")
    recipient_id = fields.Many2one('res.partner', string=u"Recipient")
    bus_username = fields.Char(u"BUS user name", related='recipient_id.bus_username', readonly=True, store=True)
    model = fields.Char(u"Model")
    # TODO: autres types de récception bus à implémenter
    bus_reception_treatment = fields.Selection([('simple_reception', u"Simple reception")],
                                               u"Treatment in BUS database", required=True)
    treatment_type = fields.Selection([('synchronization', u"Synchronization"),
                                       ('deletion', u"Deletion")],
                                      string=u"Treatment type", required=True)
    init_conf = fields.Boolean(u"Init conf")
    last_transfer_state = fields.Selection([('running', u"Running"),
                                            ('done', u"Done"),
                                            ('error', u"Error"),
                                            ('never_processed', u"Never processed")],
                                           string=u'Last transfer status', compute="_compute_last_transfer_state")
    traitement_serial = fields.Char(u"Treatment")
    chunk = fields.Integer(u"Export chunk size")
    domain = fields.Char(u"Domain", required=True, help=u"""
        You can see the additional object/functions in the model bus.backend.batch.
        You can acces to : relativedelta, self, context.
        For datetime use shorcut date, date_to_str to translate dates.
        last_send_date to get the last date of dispatch.""")

    @api.multi
    def _compute_last_transfer_state(self):
        for rec in self:
            histo = self.env['bus.backend.batch.histo'].search([('serial_id', '=', rec.traitement_serial)],
                                                                     order="create_date desc", limit=1)
            rec.last_transfer_state = histo and histo.state or 'never_processed'

    @api.multi
    def run_batch(self):
        self.ensure_one()
        if self.treatment_type == 'synchronization':
            self.export_message_synchro()
        if self.treatment_type == 'deletion':
            self.export_message_synchro(deletion=True)

    @api.multi
    def create_cron(self):
        self.write({
            'init_conf': True
        })
        item = {
            'bus_bakend_id': self.id,
            'name': u"batch d'export de type : %s -- > de %s pour %s --" % (self.display_name,
                                                                            self.backend_id.sender_id.name,
                                                                            self.recipient_id.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'days',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': 'bus.backend.batch',
            'function': 'export_message_synchro',
            'args': "(%s)" % repr([self.id]),
            'active': True
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(['&', ('bus_bakend_id', '=', self.id),
                                           '|', ('active', '=', False), ('active', '=', True)])
        if not cron:
            cron = self._create_cron()
        return {
            'name': 'Cron',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.cron',
            'res_id': cron.id,
            'context': False
        }

    @api.multi
    def get_serial(self, model_name, domain, export_ids):
        histo = self.env["bus.backend.batch.histo"].create({
            'batch_id': self.id,
            'name': u"%s : %s -> [%s]" % (model_name, domain, export_ids)
        })
        histo.serial_id = histo.id
        self.traitement_serial = histo.id

    @api.multi
    def export_message_synchro(self, deletion=False):
        self.ensure_one()
        param = self.env[self.model].search([('bus_batch_id', '=', self.id)])
        if param:
            export_chunk = param and param.chunk or False
            export_domain = param and param.domain and safe_eval(param.domain, self.export_domain_keywords()) or []
            if not deletion and param.model.deactivated_sync and 'active' in self.env[param.model.name]._fields:
                export_domain += ['|', ('active', '=', False), ('active', '=', True)]
            ids_to_export = self.env[param.model].search(export_domain)
            message_list = []
            if export_chunk:
                while ids_to_export:
                    chunk = ids_to_export[:export_chunk]
                    ids_to_export = ids_to_export[export_chunk:]
                    self.get_serial(param.model.name, param.domain, chunk.ids)
                    message_list.append({
                        'header': {
                            'origin': self.backend_id.bus_username,
                            'dest': self.bus_username,
                            'treatment': self.treatment_type,
                            'serial_id': self.traitement_serial,
                        },
                        'export': {'model': chunk._name, 'ids': chunk.ids}
                    })
            else:
                self.get_serial(param.model.name, param.domain, ids_to_export.ids)
                message_list.append({
                    'header': {
                        'origin': self.backend_id.bus_username,
                        'dest': self.bus_username,
                        'treatment': self.treatment_type,
                        'serial_id': self.traitement_serial,
                    },
                    'export': {'model': ids_to_export._name, 'ids': ids_to_export.ids}
                })
            for message_dict in message_list:
                serial_id = message_dict.get('header').get('serial_id')
                histo = self.env['bus.backend.batch.histo'].search([('serial_id', '=', serial_id)])
                description = u"%s: %s - %s" % (self.name, histo.id, param.model.name)
                job_uid = job_generate_message.delay(ConnectorSession.from_env(self.env), self.backend_id._name,
                                                     self.backend_id.name,
                                                     message_dict, name=serial_id,
                                                     description=description,
                                                     bus_reception_treatment=self.bus_reception_treatment,
                                                     deletion=deletion)
                self.env['bus.backend.batch.histo.log'].create({
                    'histo_id': serial_id,
                    'log': u"SEND : %s" % self.treatment_type,
                    'state': u'running',
                    'job_uid': job_uid,
                })
        return True

    @api.multi
    def export_domain_keywords(self):
        self.ensure_one()
        return {
            'date': datetime,
            'relativedelta': relativedelta.relativedelta,
            'self': self,
            'context': self.env.context,
            'date_to_str': fields.Date.to_string,
            'last_send_date': self.get_last_send_date()
        }

    @api.multi
    def get_last_send_date(self):
        self.ensure_one()
        histo = self.env['bus.backend.batch.histo'].search([('batch_id', '=', self.id)], order='create_date DESC',
                                                                 limit=1)
        log = self.env['bus.backend.batch.histo.log'].search([('histo_id', '=', histo.id)],
                                                                   order='create_date DESC', limit=1)
        return log.create_date

    @api.model
    def generate_message(self, param, deletion=False):
        message_dict = {
            'header': param.get('header'),
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        export_ids = self.env[param.get('export').get('model')].search([('id', 'in', param.get('export').get('ids'))])
        if deletion:
            result = self._generate_msg_body_deletion(export_ids, param)
        else:
            result = self._generate_msg_body(export_ids, param)
        message_dict['body'] = result['body']
        return message_dict

    def _generate_msg_body_deletion(self, export_ids, param):
        # Ne gère que le model bus.receive.transfer
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        model_name = param.get('export').get('model')
        object_mapping = self.env['bus.object.mapping'].search([('name', '=', model_name)])
        for export_id in export_ids:
            if not message_dict['body']['root'].get(model_name):
                message_dict['body']['root'][model_name] = {}
            message_dict['body']['root'][model_name][str(export_id.id)] = {'id': export_id.id}
            if object_mapping.key_xml_id:
                ir_model_data = self.env['ir.model.data'].search(
                    [('model', '=', object_mapping.name), ('res_id', '=', export_id.id)])
                if ir_model_data:
                    message_dict['body']['root'][object_mapping.name][str(export_id.id)].update(
                        {'xml_id': ir_model_data.complete_name})
            list_export_field = [x for x in object_mapping.field_ids if x.export_field]
            for field in list_export_field:
                message_dict['body']['root'][object_mapping.name][str(export_id.id)][field.map_name] = \
                    export_id[field.name]
            if not message_dict['body']['dependency'].get(export_id.model):
                message_dict['body']['dependency'][export_id.model] = {}
            if not message_dict['body']['dependency'][export_id.model].get(str(export_id.local_id)):
                message_dict['body']['dependency'][export_id.model][export_id.local_id] = {
                    'id': export_id.local_id
                }
        return message_dict

    def _generate_msg_body(self, export_ids, param):
        message_dict = {
            'body': {
                'root': {},
                'dependency': {},
            }
        }
        model_name = param.get('export').get('model')
        object_mapping = self.env['bus.object.mapping'].search([('name', '=', model_name)])
        for export_id in export_ids:
            if not message_dict['body']['root'].get(model_name):
                message_dict['body']['root'][model_name] = {}
            message_dict['body']['root'][model_name][str(export_id.id)] = {'id': export_id.id}
            if object_mapping.key_xml_id:
                ir_model_data = self.env['ir.model.data'].search(
                    [('model', '=', object_mapping.name), ('res_id', '=', export_id.id)])
                if ir_model_data:
                    message_dict['body']['root'][object_mapping.name][str(export_id.id)].update(
                        {'xml_id': ir_model_data.complete_name})
            list_export_field = [x for x in object_mapping.field_ids if x.export_field]
            for field in list_export_field:
                if field.type_field == 'many2many' and field.name in export_id and export_id[field.name]:
                    message_dict['body']['root'][object_mapping.name][str(export_id.id)][field.map_name] = {
                        'ids': export_id[field.name].ids,
                        'model': field.relation,
                        'type_field': 'many2many'
                    }
                    if not message_dict['body']['dependency'].get(field.relation):
                        message_dict['body']['dependency'][field.relation] = {}

                    for sub_field in export_id[field.name]:
                        if not message_dict['body']['dependency'][field.relation].get(str(sub_field.id)):
                            message_dict['body']['dependency'][field.relation][str(sub_field.id)] = {
                                'id': sub_field.id
                            }
                            message_dict = self.generate_dependency(message_dict, field.relation, sub_field.id)
                if field.type_field == 'many2one' and field.name in export_id and export_id[field.name]:
                    message_dict['body']['root'][object_mapping.name][str(export_id.id)][field.map_name] = {
                        'id': export_id[field.name].id,
                        'model': field.relation,
                        'type_field': 'many2one'
                    }
                    if not message_dict['body']['dependency'].get(field.relation):
                        message_dict['body']['dependency'][field.relation] = {}
                    if not message_dict['body']['dependency'][field.relation].get(str(export_id[field.name].id)):
                        message_dict['body']['dependency'][field.relation][str(export_id[field.name].id)] = {
                            'id': export_id[field.name].id
                        }
                        message_dict = self.generate_dependency(message_dict, field.relation, export_id[field.name].id)
                elif field.type_field == 'primary' and field.name in export_id:
                    message_dict['body']['root'][object_mapping.name][str(export_id.id)][field.map_name] = \
                        export_id[field.name]
                    if field.name in export_id._fields and export_id._fields[field.name].type == 'char' and \
                            export_id._fields[field.name].translate:
                        translations = self.env['ir.translation'].search(
                            [('name', '=', export_id._name + ',' + field.name), ('res_id', '=', export_id.id)])
                        if translations:
                            message_dict = self.generate_translation(message_dict, object_mapping, export_id, field, translations)
        return message_dict

    @api.model
    def generate_translation(self, message_dict, object_mapping, export_id, field, translations):
        if not message_dict['body']['root'][object_mapping.name][str(export_id.id)].get('translation'):
            message_dict['body']['root'][object_mapping.name][str(export_id.id)]['translation'] = {}
        if not message_dict['body']['root'][object_mapping.name][str(export_id.id)]['translation'].get(
                field.map_name):
            message_dict['body']['root'][object_mapping.name][str(export_id.id)]['translation'][
                field.map_name] = {}
            for translation in translations:
                message_dict['body']['root'][object_mapping.name][str(export_id.id)]['translation'].update({
                    field.map_name: {
                        translation.lang: {
                            'source': translation.source,
                            'value': translation.value
                        }
                    }
                })
        return message_dict

    @api.model
    def generate_dependency(self, message_dict, model, id):
        map = self.env['bus.object.mapping'].search([('name', '=', model),
                                                 ('transmit', '=', True)])
        map_field = self.env['bus.object.mapping.field'].search([('type_field', '=', 'many2one'),
                                                             ('export_field', '=', True),
                                                             ('object_id', '=', map.id)])
        export_id = self.env[model].browse(id)
        for field in map_field:
            if export_id[field.name]:
                if not message_dict['body']['dependency'].get(field.relation):
                    message_dict['body']['dependency'][field.relation] = {}
                if not message_dict['body']['dependency'][field.relation].get(str(export_id[field.name].id)):
                    message_dict['body']['dependency'][field.relation][str(export_id[field.name].id)] = {
                        'id': export_id[field.name].id
                    }
                    message_dict = self.generate_dependency(message_dict, field.relation, export_id[field.name].id)
        return message_dict
