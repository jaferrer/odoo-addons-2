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
from .. import jobs


class BusextendBackendBatch(models.Model):
    _name = 'busextend.backend.batch'

    backend_id = fields.Many2one("busextend.backend", string="Backend")

    destinataire = fields.Many2one("res.partner", string="Destinataire")
    identifiant = fields.Char('Identifiant', compute="_get_identifiant_bus", readonly=True, store=True)
    commentaire = fields.Char('commentaire')
    model = fields.Char('Model')
    code_recep = fields.Char('code_recepteur')
    actif = fields.Boolean(u'Active', compute="_compute_cron")
    type_id = fields.Many2one('traitement.type', string=u"Type Traitement", required=True)
    init_conf = fields.Boolean('Init conf', store=True)
    last_transfert = fields.Selection([(u"INPROGRESS", u"En Cours"),
                                       (u"DONE", u"Réussi"),
                                       (u"ERROR", u"Erreur"),
                                       (u"NOTRT", u"Jamais Traité")],
                                      string=u'Etat Dernier tranfert', compute="_compute_last_statut")
    traitement_serial = fields.Char('traitement')

    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", related="destinataire.image")

    @api.multi
    @api.depends('destinataire')
    def _get_identifiant_bus(self):
        for rec in self:
            rec.identifiant = rec.destinataire.identifiant_bus

    @api.multi
    def _compute_cron(self):
        for rec in self:
            cron = self.env['ir.cron'].search([('bus_id', '=', rec.id)])
            if cron:
                rec.actif = cron.active
            else:
                rec.actif = u"NOTRT"

    @api.multi
    def _compute_last_statut(self):
        for rec in self:
            histo = self.env['busextend.backend.batch.histo'].search([('serial_id', '=', rec.traitement_serial)],
                                                                     order="create_date desc", limit=1)
            if histo:
                rec.last_transfert = histo.state

    @api.multi
    def open_popup_parameter(self):
        self.ensure_one()
        param = self.env[self.type_id.model_param_name].search([('bus_batch_id', '=', self.id)])
        ctx = dict(self.env.context)
        if not param:
            ctx['default_bus_batch_id'] = self.id
        act = {
            'name': 'Parameter',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.type_id.model_param_name,
            'target': 'new',
            'context': ctx
        }
        if param:
            act['res_id'] = param[0].id
        return act

    @api.multi
    def run_batch(self):
        self.ensure_one()
        getattr(self, self.type_id.method_name)()

    @api.multi
    def create_cron(self):
        self.write({
            "init_conf": True
        })
        item = {
            'bus_id': self.id,
            'name': u"batch d'export de type : %s -- > de %s pour %s --" % (self.display_name,
                                                                            self.backend_id.emetteur.name,
                                                                            self.destinataire.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'days',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': 'busextend.backend.batch',
            'function': u'%s' % (self.type_id.method_name),
            'args': "(%s)" % repr([self.id]),
            'active': True
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(
            ['&', ('bus_id', '=', self.id), '|', ('active', '=', False), ('active', '=', True)])
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
        histo = self.env["busextend.backend.batch.histo"].create({
            "batch_id": self.id,
            "name": "%s : %s -> [%s]" % (model_name, domain, export_ids)
        })
        histo.serial_id = histo.id
        self.traitement_serial = histo.id

    @api.multi
    def export_message_synchro_deletion(self):
        param = self.env[self.type_id.model_param_name].search([('bus_batch_id', '=', self.id)])
        if param:
            export_domain = param and param.domain and safe_eval(param.domain, self.export_domain_keywords()) or []
            export_chunk = param and param.chunk or False
            export_ids = self.env[param.model.name].search(export_domain)
            ids = []
            if export_chunk:
                while export_ids:
                    chunk = export_ids[:export_chunk]
                    export_ids = export_ids[export_chunk:]
                    self.get_serial(param.model.name, param.domain, chunk.ids)
                    ids.append({
                        "header": {
                            "origin": self.backend_id.identifiant,
                            "dest": self.identifiant,
                            "type_message_code": "SIRAIL_SYNCHRO_DELETION",
                            "serial_id": self.traitement_serial,
                        },
                        "export": {"model": chunk._name, "ids": chunk.ids}
                    })
            else:
                self.get_serial(param.model.name, param.domain, export_ids.ids)
                ids.append({
                    "header": {
                        "origin": self.backend_id.identifiant,
                        "dest": self.identifiant,
                        "type_message_code": "SIRAIL_SYNCHRO_DELETION",
                        "serial_id": self.traitement_serial,
                    },
                    "export": {"model": export_ids._name, "ids": export_ids.ids}
                })
            for ids_msg in ids:
                serial_id = ids_msg.get("header").get("serial_id")
                histo = self.env['busextend.backend.batch.histo'].browse(serial_id)
                jobs.generate_message_deletion.delay(ConnectorSession.from_env(self.env), "bus.model.extend", 0,
                                                     ids_msg,
                                                     name=serial_id,
                                                     description="SIRAIL_SYNCHRO_DELETION: %s - %s" % (
                                                         histo.id, param.model.name),
                                                     code_recep=self.code_recep)
                self.env["busextend.backend.batch.histo.log"].create({
                    "histo_id": serial_id,
                    "serial_id": serial_id,
                    "log": u"SEND : SYNCHRO DELETION",
                    "state": u"INPROGRESS"
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
        histo = self.env["busextend.backend.batch.histo"].search([("batch_id", "=", self.id)], order="create_date DESC",
                                                                 limit=1)
        log = self.env['busextend.backend.batch.histo.log'].search([('histo_id', '=', histo.id)],
                                                                   order='create_date DESC', limit=1)
        return log.create_date

    @api.multi
    def export_message_synchro(self):
        param = self.env[self.type_id.model_param_name].search([('bus_batch_id', '=', self.id)])
        if param:
            export_chunk = param and param.chunk or False
            export_domain = param and param.domain and safe_eval(param.domain, self.export_domain_keywords()) or []
            if param.model.deactivated_sync and 'active' in self.env[param.model.name]._fields:
                export_domain += ['|', ('active', '=', False), ('active', '=', True)]
            export_ids = self.env[param.model.name].search(export_domain)
            ids = []
            if export_chunk:
                while export_ids:
                    chunk = export_ids[:export_chunk]
                    export_ids = export_ids[export_chunk:]
                    self.get_serial(param.model.name, param.domain, chunk.ids)
                    ids.append({
                        "header": {
                            "origin": self.backend_id.identifiant,
                            "dest": self.identifiant,
                            "type_message_code": "SIRAIL_SYNCHRO",
                            "serial_id": self.traitement_serial,
                        },
                        "export": {"model": chunk._name, "ids": chunk.ids}
                    })
            else:
                self.get_serial(param.model.name, param.domain, export_ids.ids)
                ids.append({
                    "header": {
                        "origin": self.backend_id.identifiant,
                        "dest": self.identifiant,
                        "type_message_code": "SIRAIL_SYNCHRO",
                        "serial_id": self.traitement_serial,
                    },
                    "export": {"model": export_ids._name, "ids": export_ids.ids}
                })
            for ids_msg in ids:
                serial_id = ids_msg.get("header").get("serial_id")
                histo = self.env['busextend.backend.batch.histo'].search([('serial_id', '=', serial_id)])
                job_uid = jobs.job_generate_message.delay(ConnectorSession.from_env(self.env), "bus.model.extend", 0,
                                                          ids_msg, name=serial_id,
                                                          description="SIRAIL_SYNCHRO: %s - %s" % (
                                                          histo.id, param.model.name),
                                                          code_recep=self.code_recep)
                self.env["busextend.backend.batch.histo.log"].create({
                    "histo_id": serial_id,
                    "log": u"SEND : SYNCHRO",
                    "state": u"INPROGRESS",
                    "job_uid": job_uid,
                })
        return True

    @api.model
    def generate_message_deletion(self, param):
        msg = {
            "header": param.get('header'),
            "body": {
                "root": {},
                "dependency": {},
            }
        }
        export_ids = self.env[param.get('export').get('model')].search([('id', 'in', param.get('export').get('ids'))])
        result = self._generate_msg_body_deletion(export_ids, param)
        msg["body"] = result["body"]
        return msg

    @api.model
    def generate_message(self, param):
        msg = {
            "header": param.get('header'),
            "body": {
                "root": {},
                "dependency": {},
            }
        }
        export_ids = self.env[param.get('export').get('model')].browse(param.get('export').get('ids'))
        result = self._generate_msg_body(export_ids, param)
        msg["body"] = result["body"]
        return msg

    def _generate_msg_body_deletion(self, export_ids, param):
        # Ne gère que le model bus.model.extend
        msg = {
            "body": {
                "root": {},
                "dependency": {},
            }
        }
        model_name = param.get("export").get("model")
        object_mapping = self.env['object.mapping'].search([('name', '=', model_name)])
        for export_id in export_ids:
            if not msg["body"]["root"].get(model_name):
                msg["body"]["root"][model_name] = {}
            msg["body"]["root"][model_name][str(export_id.id)] = {"id": export_id.id}
            if object_mapping.key_xml_id:
                ir_model_data = self.env['ir.model.data'].search(
                    [('model', '=', object_mapping.name), ('res_id', '=', export_id.id)])
                if ir_model_data:
                    msg["body"]["root"][object_mapping.name][str(export_id.id)].update(
                        {"xml_id": ir_model_data.complete_name})
            list_export_field = [x for x in object_mapping.field_ids if x.export_field]
            for field in list_export_field:
                msg["body"]["root"][object_mapping.name][str(export_id.id)][field.map_name] = \
                    export_id[field.name]
            if not msg["body"]["dependency"].get(export_id.model):
                msg["body"]["dependency"][export_id.model] = {}
            if not msg["body"]["dependency"][export_id.model].get(str(export_id.openerp_id)):
                msg["body"]["dependency"][export_id.model][export_id.openerp_id] = {
                    "id": export_id.openerp_id
                }
        return msg

    def _generate_msg_body(self, export_ids, param):
        msg = {
            "body": {
                "root": {},
                "dependency": {},
            }
        }
        model_name = param.get("export").get("model")
        object_mapping = self.env['object.mapping'].search([('name', '=', model_name)])
        for export_id in export_ids:
            if not msg["body"]["root"].get(model_name):
                msg["body"]["root"][model_name] = {}
            msg["body"]["root"][model_name][str(export_id.id)] = {"id": export_id.id}
            if object_mapping.key_xml_id:
                ir_model_data = self.env['ir.model.data'].search(
                    [('model', '=', object_mapping.name), ('res_id', '=', export_id.id)])
                if ir_model_data:
                    msg["body"]["root"][object_mapping.name][str(export_id.id)].update(
                        {"xml_id": ir_model_data.complete_name})
            list_export_field = [x for x in object_mapping.field_ids if x.export_field]
            for field in list_export_field:
                if field.type_field == "M2M" and field.name in export_id and export_id[field.name]:
                    msg["body"]["root"][object_mapping.name][str(export_id.id)][field.map_name] = {
                        "ids": export_id[field.name].ids,
                        "model": field.relation,
                        "type_field": "M2M"
                    }
                    if not msg["body"]["dependency"].get(field.relation):
                        msg["body"]["dependency"][field.relation] = {}

                    for sub_field in export_id[field.name]:
                        if not msg["body"]["dependency"][field.relation].get(str(sub_field.id)):
                            msg["body"]["dependency"][field.relation][str(sub_field.id)] = {
                                "id": sub_field.id
                            }
                            msg = self.generate_dependency(msg, field.relation, sub_field.id)
                if field.type_field == "M2O" and field.name in export_id and export_id[field.name]:
                    msg["body"]["root"][object_mapping.name][str(export_id.id)][field.map_name] = {
                        "id": export_id[field.name].id,
                        "model": field.relation,
                        "type_field": "M2O"
                    }
                    if not msg["body"]["dependency"].get(field.relation):
                        msg["body"]["dependency"][field.relation] = {}
                    if not msg["body"]["dependency"][field.relation].get(str(export_id[field.name].id)):
                        msg["body"]["dependency"][field.relation][str(export_id[field.name].id)] = {
                            "id": export_id[field.name].id
                        }
                        msg = self.generate_dependency(msg, field.relation, export_id[field.name].id)
                elif field.type_field == "PRIMARY" and field.name in export_id:
                    msg["body"]["root"][object_mapping.name][str(export_id.id)][field.map_name] = \
                        export_id[field.name]
                    if field.name in export_id._fields and export_id._fields[field.name].type == "char" and \
                            export_id._fields[field.name].translate:
                        translations = self.env['ir.translation'].search(
                            [('name', '=', export_id._name + "," + field.name), ('res_id', '=', export_id.id)])
                        if translations:
                            msg = self.generate_translation(msg, object_mapping, export_id, field, translations)
        return msg

    @api.model
    def generate_translation(self, msg, object_mapping, export_id, field, translations):
        if not msg["body"]["root"][object_mapping.name][str(export_id.id)].get('translation'):
            msg["body"]["root"][object_mapping.name][str(export_id.id)]['translation'] = {}
        if not msg["body"]["root"][object_mapping.name][str(export_id.id)]['translation'].get(
                field.map_name):
            msg["body"]["root"][object_mapping.name][str(export_id.id)]['translation'][
                field.map_name] = {}
            for translation in translations:
                msg["body"]["root"][object_mapping.name][str(export_id.id)]['translation'].update({
                    field.map_name: {
                        translation.lang: {
                            'source': translation.source,
                            'value': translation.value
                        }
                    }
                })
        return msg

    @api.model
    def generate_dependency(self, msg, model, id):
        map = self.env["object.mapping"].search([("name", "=", model),
                                                 ("transmit", '=', True)])
        map_field = self.env["object.mapping.field"].search([("type_field", "=", "M2O"),
                                                             ("export_field", '=', True),
                                                             ("object_id", "=", map.id)])
        export_id = self.env[model].browse(id)
        for field in map_field:
            if export_id[field.name]:
                if not msg["body"]["dependency"].get(field.relation):
                    msg["body"]["dependency"][field.relation] = {}
                if not msg["body"]["dependency"][field.relation].get(str(export_id[field.name].id)):
                    msg["body"]["dependency"][field.relation][str(export_id[field.name].id)] = {
                        "id": export_id[field.name].id
                    }
                    msg = self.generate_dependency(msg, field.relation, export_id[field.name].id)
        return msg
