# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp.addons.data_bus_system_backend.transpo import IndexBus


@job(default_channel='root.reception')
def traitement_reception(session, model_name, recepteur_id, archive, archive_id):
    recep = session.pool[model_name].browse(session.cr, session.uid, recepteur_id)
    recep.exec_recep_seq(archive, archive_id, state="IDENT")
    return "OK"


@job(default_channel='root.distribution')
def traitement_distribution(session, model_name, archive, archive_id):
    archive_msg = session.env[model_name].browse(archive_id)
    archive_msg.exec_distri_seq(archive)


@job(default_channel='root.identification')
def traitement_ident(session, model_name, archive, archive_id):
    archive_msg = session.env[model_name].browse(archive_id)
    archive_msg.exec_distri_seq(archive)


@job(default_channel='root.indexation')
def traitement_index(session, model_name, archive, archive_id):
    archive_msg = session.env[model_name].browse(archive_id)
    archive_msg.exec_distri_seq(archive)


@job(default_channel='root.reception.replay')
def traitement_reception_replay(session, model_name, recepteur_id, archive, archive_id):
    recep = session.pool[model_name].browse(session.cr, session.uid, recepteur_id)
    recep.exec_recep_seq(archive, archive_id, state="IDENT")
    return "OK"

class MessageType(models.Model):
    _name = 'message.type'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    code = fields.Char(string=u'Code', required=True, index=True)
    index_id = fields.Many2one('module.dynamique', string=u"Indexeur",
                               domain='[("type", "=", "INDEX")]')

    _sql_constraints = [
        ('code_uniq', 'unique(code)',
         'Le code du type message exist deja.'),
        ('name_uniq', 'unique(name)',
         'Le nom du type message exist deja')
    ]


class BackendHomeCron(models.Model):
    _inherit = 'ir.cron'

    recep_id = fields.Many2one('recepteur', string=u"recepteur")


class Recepteur(models.Model):
    _name = 'recepteur'

    name = fields.Char(string=u'Name', required=True, index=True)
    code = fields.Char(string=u'Code', required=True, index=True)
    description = fields.Text(string=u'Description')
    ident_id = fields.Many2one('module.dynamique', string=u"Identificateur",
                               domain='[("type", "=", "IDENT")]')
    actif = fields.Boolean(u'Active', compute="_compute_cron")
    type_id = fields.Many2one('connector.type', string=u"Type Récepteur", required=True,
                              domain='[("type", "=", "RECEP")]')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", related="type_id.image")
    range = fields.Integer(string=u'Traitement simultané')
    init_conf = fields.Boolean('Init conf', store=True)

    @api.multi
    def _compute_cron(self):
        for rec in self:
            cron = self.env['ir.cron'].search([('recep_id', '=', rec.id)])
            if cron:
                rec.actif = cron.active
            else:
                rec.actif = False

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
            'recep_id': self.id,
            'name': u"Recepteur %s pour %s" % (self.name, self.type_id.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'hours',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': 'recepteur',
            'function': u'%s' % (self.type_id.method_name),
            'args': "(%s)" % repr([self.id]),
            'active': False
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(
            ['&', ('recep_id', '=', self.id), '|', ('active', '=', False), ('active', '=', True)])
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
    def unlink(self):
        crons = self.env['ir.cron'].search(
            ['&', ('recep_id', 'in', self.ids), '|', ('active', '=', False), ('active', '=', True)])
        if crons:
            crons.unlink()

        for rec in self:
            rec.active = False

    @api.multi
    def open_popup_parameter(self):
        self.ensure_one()
        param = self.env[self.type_id.model_param_name].search([('recep_id', '=', self.id)])
        if not param:
            param = self.env[self.type_id.model_param_name].create({
                'recep_id': self.id
            })
        return {
            'name': 'Parameter',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.type_id.model_param_name,
            'res_id': param[0].id,
            'target': 'new',
            'context': False
        }

    @api.multi
    def exec_recep_seq(self, archive, archive_id, state):
        try:
            archive_msg = self.env['archive'].browse(archive_id)
            if state == "IDENT":
                if self.ident_id:
                    getattr(self, self.ident_id.method_name)(archive, archive_id)
                else:
                    self.exec_recep_seq(archive, archive_id, state="DISTRI")
            elif state == "INDEX":
                if archive_msg.type_message_id == self.env.ref('data_bus_system_backend.message_inconnu'):
                    self.exec_indexeur(archive, archive_id, IndexBus())
                elif archive_msg.type_message_id.index_id:
                    getattr(self,
                            archive_msg.type_message_id.index_id.method_name)(archive,
                                                                              archive_id,
                                                                              archive_msg.type_message_id.id)
                else:
                    self.exec_recep_seq(archive, archive_id, state="DISTRI")
            elif state == "DISTRI":
                new_ctx = dict(self.env.context)
                session = ConnectorSession(self.env.cr, self.env.uid,
                                           context=new_ctx)
                traitement_distribution.delay(
                    session, 'archive', archive, archive_id, priority=3
                )
        except Exception as e:
            archive_msg.create_log({
                'archive_id': archive_id,
                'state': 'ERROR',
                'log': e.message
            })
        return "OK"

    @api.multi
    def exec_identificateur(self, archive, archive_id, code):
        type_message = self.env['message.type'].search([('code', '=', code)])
        if not type_message :
            type_message = self.env.ref('data_bus_system_backend.message_inconnu')
        archive_msg = self.env['archive'].browse(archive_id)

        archive_msg.write({
            'type_message_id': type_message.id
        })
        archive_msg.create_log({
            'archive_id': archive_msg.id,
            'state': 'IDENTIFIE',
            'log': type_message.name
        })
        self.exec_recep_seq(archive, archive_id, state="INDEX")
        return "OK"

    @api.multi
    def exec_indexeur(self, archive, archive_id, index):

        archive_msg = self.env['archive'].browse(archive_id)

        if isinstance(index, IndexBus):
            error = False
            log = u""
            if not index.type_message_id:
                error = True
                log += u"Le type messsage n'est pas communiqué\n"
            if not index.dest:
                error = True
                log += u"Aucun destinataire de trouvé.\n"
            if error:
                archive_msg.create_log({
                    'archive_id': archive_msg.id,
                    'state': 'ERROR',
                    'log': log
                })
            else:

                origin = self.env["application.config"].search([('identifiant', '=', index.origin),
                                                                ('type_id', "=",
                                                                index.type_message_id)])
                dest = self.env["application.config"].search([('identifiant', '=', index.dest),
                                                              ('type_id', "=",
                                                               index.type_message_id)])

                archive_msg.write({
                    "origin": origin and origin.application.id or False,
                    "origin_code": index.origin,
                    "dest_code": index.dest,
                    "dest": dest and dest.application.id or False,
                    'mot_cles': str(index.motcles),
                    "archive_parent_id": index.archive_principal
                })

                archive_msg.create_log({
                    'archive_id': archive_msg.id,
                    'state': 'INDEX',
                    'log': str(index.__dict__)
                })

                self.exec_recep_seq(archive, archive_id, state="DISTRI")

        else:
            archive_msg.create_log({
                'archive_id': archive_msg.id,
                'state': 'ERROR',
                'log': u"L'indexeur n'a rien retourné"
            })
        return "OK"


class Traitement(models.Model):
    _name = 'connector.type'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    model_param_name = fields.Char(string=u'Model Name')
    method_name = fields.Char(string=u'Method Name')
    type = fields.Selection([("RECEP", "Connecteur RECEP"),
                             ("DISTRI", "MConnecteur DISTRI")
                             ],
                            string=u"Type", required=True)

    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.")


class Module(models.Model):
    _name = 'module.dynamique'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    method_name = fields.Char(string=u'Method Name')
    type = fields.Selection([("IDENT", "Module d'identification"),
                             ("TRT", "Module de traitement"),
                             ("INDEX", 'Indexeur')
                             ],
                            string=u"Type", required=True)


class Traitement(models.Model):
    _name = 'traitement'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    type_id = fields.Many2one('message.type', string=u"Type Message", required=True)
    traitement_lines = fields.One2many(
        comodel_name='traitement.config',
        inverse_name='traitement_id',
        string="Sequence de traitement",
    )
    compute_nb_trt = fields.Integer("", compute="_compute_nb_trt")

    @api.multi
    def _compute_nb_trt(self):
        for rec in self:
            rec.compute_nb_trt = len(rec.traitement_lines)


class ConfigTraitement(models.Model):
    _name = 'traitement.config'

    traitement_id = fields.Many2one('traitement', string=u"Traitement",
                                           required=True)
    traitement_module_id = fields.Many2one('module.dynamique', string=u"Type Distributeur",
                                           required=True,
                                           domain='[("type", "=", "TRT")]')
    sequence = fields.Integer(string=u'Sequence')



class Distributeur(models.Model):
    _name = 'distributeur'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    type_id = fields.Many2one('connector.type', string=u"Type Distributeur", required=True,
                              domain='[("type", "=", "DISTRI")]')
    image = fields.Binary("Photo", attachment=True,
                          help="This field holds the image used as image for the cateogry, limited to "
                               "1024x1024px.", related="type_id.image")

    @api.multi
    def open_popup_parameter(self):
        self.ensure_one()
        param = self.env[self.type_id.model_param_name].search([('distributeur_id', '=', self.id)])
        if not param:
            param = self.env[self.type_id.model_param_name].create({
                'distributeur_id': self.id
            })
        return {
            'name': 'Parameter',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.type_id.model_param_name,
            'res_id': param.id,
            'target': 'new',
            'context': False
        }


class Application(models.Model):
    _name = 'application.config'

    application = fields.Many2one('application', string=u"Origine")
    identifiant = fields.Char(string=u'identifiant', required=True, index=True)
    type_id = fields.Many2one('message.type', string=u"Type Message", required=True)


class ConfigDistributeur(models.Model):
    _name = 'distributeur.config'

    distributeur_id = fields.Many2one('distributeur', string=u"Distributeur", required=True)
    type_id = fields.Many2one('message.type', string=u"Type Message", required=True)
    origine = fields.Many2one('application', string=u"Origine")
    dest = fields.Many2one('application', string=u"Destination", required="1")
    traitement_id = fields.Many2one('traitement', string=u"Traitement")


class Application(models.Model):
    _name = 'application'

    name = fields.Char(string=u'Name', required=True, index=True)
    description = fields.Text(string=u'Description')
    identifiant = fields.Char(string=u'identifiant', index=True)
    config_lines = fields.One2many(
        comodel_name='application.config',
        inverse_name='application',
        string="Identifiant Application",
    )
    config_distri_origine_lines = fields.One2many(
        comodel_name='distributeur.config',
        inverse_name='origine',
        string="Origine distribution",
    )

    config_distri_dest_lines = fields.One2many(
        comodel_name='distributeur.config',
        inverse_name='dest',
        string="Destination distribution",
    )

    _sql_constraints = [
        ('identifiant_uniq', 'unique(code)',
         'Le code exist deja.'),
        ('name_uniq', 'unique(name)',
         'Le nom exist deja')
    ]


class TypeMessage(models.Model):
    _name = 'archive'
    _order = 'id desc'

    state = fields.Selection([("RECU", u"Reçu"),
                              ("REPLAY", u"Rejoué"),
                              ("IDENTIFIE", u"Identifié"),
                              ("INDEX", u'Indexé'),
                              ("TRT", u'Traité' ),
                              ("DISTRIBUE", u'Distribué'),
                              ("OK", u'Validé'),
                              ("ERROR", u'Erreur'),
                              ("NOK", u'Non Validé'),
                              ("CANCEL", u"Annuler")])

    message = fields.Text(string=u'Message')
    message_name = fields.Char(string=u'Nom fichier Source')
    recep_id = fields.Many2one('recepteur', string=u"Recepteur", required=True)
    type_message_id = fields.Many2one('message.type', string=u"Type Message", required=True)
    dest_code = fields.Char(string=u'Code destinataire')
    origin_code = fields.Char(string=u'Code origine')
    mot_cles = fields.Char(string=u'Index', index=True)
    origin = fields.Many2one('application', string=u"Origine")
    dest = fields.Many2one('application', string=u"Destination")
    archive_parent_id = fields.Many2one('archive', string=u"archive parent")
    logs_id = fields.One2many(
        comodel_name='archive.log',
        inverse_name='archive_id',
        string="Logs du traitement"
    )

    @api.multi
    def exec_distri_seq(self, archive):
        try:
            exec_dict = []
            distri_config_ids = self.env["distributeur.config"].search([("dest", "=", self.dest.id),
                                                              ("type_id", "=", self.type_message_id.id)])

            for item in distri_config_ids:
                trt_seq = {}
                trt_seq["archive"] = archive
                if item.traitement_id:
                    for trt_id in item.traitement_id.traitement_lines:
                        trt_seq["archive"] = getattr(self, trt_id.traitement_module_id.method_name)(trt_seq["archive"], self.id)
                        self.create_log({
                            'archive_id': self.id,
                            'state': 'TRT',
                            'log': u"le message est traité par le module %s" % (trt_id.traitement_module_id.name),
                            'message': trt_seq["archive"]
                        })
                trt_seq["distri"] = item.distributeur_id
                exec_dict.append(trt_seq)

            for ex in exec_dict:
                getattr(ex["distri"], ex["distri"].type_id.method_name)(ex["archive"], self.id)
        except Exception as e:
            self.create_log({
                'archive_id': self.id,
                'state': 'ERROR',
                'log': e
            })

        return "ok"

    @api.multi
    def create_log(self, resp):
        self.env['archive.log'].create(resp)
        self.state = resp.get("state")
        return "ok"

    @api.multi
    def erreur_trt(self, resp):
        return {
            'name': 'Erreur traité',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'archive.log',
            'target': 'new',
            'view_id': self.env.ref("data_bus_system_backend.erreur_log_trt").id,
            'context': {'default_state': 'OK', 'default_archive_id': self.id}
        }

    @api.multi
    def run_replay(self):
        for rec in self:
            rec.create_log({
                'archive_id': rec.id,
                'state': 'REPLAY',
                'log': 'action utilisateur : REPLAY'
            })
            new_ctx = dict(self.env.context)
            session = ConnectorSession(self.env.cr, self.env.uid,
                                       context=new_ctx)
            traitement_reception_replay.delay(
                session, 'recepteur', rec.recep_id.id,
                rec.message, rec.id,
                priority=3
            )


class ArchiveLog(models.Model):
    _name = 'archive.log'
    _order = "id desc"

    state = fields.Selection([("RECU", u"Reçu"),
                              ("REPLAY", u"Rejoué"),
                              ("IDENTIFIE", u"Identifié"),
                              ("INDEX", u'Indexé'),
                              ("TRT", u'Traité' ),
                              ("DISTRIBUE", u'Distribué'),
                              ("OK", u'Validé'),
                              ("ERROR", u'Erreur'),
                              ("NOK", u'Non Validé'),
                              ("CANCEL", u"Annuler")])

    state_selection = fields.Selection([("CANCEL", u"Annuler"),
                                        ("OK", u'Validé'),
                                        ("NOK", u'Non Validé')])

    archive_id = fields.Many2one('archive', string=u"archive")
    log = fields.Text(string=u'Log')
    message = fields.Text(string=u'Message traité')

    @api.multi
    def get_message_log(self):
        return {
            'name': 'Log Détails',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'archive.log',
            'target': 'new',
            'view_id': self.env.ref("data_bus_system_backend.log_details").id,
            'res_id': self.id,
            'context': {}
        }

    @api.multi
    def save(self):
        self.archive_id.state = self.state_selection
        ajout = u"Status '%s' forcé par : %s \nMotif :\n" % (self.state_selection, self.create_uid.name)
        self.log = ajout + self.log
        return True


class Monitoring(models.Model):
    _name = 'monitoring'
    _order = 'sequence asc'

    name = fields.Char(u"nom")
    sequence = fields.Integer(u"Sequence")
    recu_in_current = fields.Integer(u"En cours de réception", compute="_compute_recu_in_current")
    recu_waiting = fields.Integer(u"En attente de réception", compute="_compute_recu_waiting")
    ident_waiting = fields.Integer(u"En attente d'identification", compute="_compute_ident_waiting")
    ident_in_current = fields.Integer(u"En cours d'identification", compute="_compute_ident_in_current")
    index_waiting = fields.Integer(u"En attente d'indexation", compute="_compute_index_waiting")
    index_in_current = fields.Integer(u"En cours d'indexation", compute="_compute_index_in_current")
    trt_waiting = fields.Integer(u"En attente d'indexation", compute="_compute_trt_waiting")
    trt_in_current = fields.Integer(u"En cours d'indexation", compute="_compute_trt_in_current")
    distri_waiting = fields.Integer(u"En attente d'indexation", compute="_compute_distri_waiting")
    distri_in_current = fields.Integer(u"En cours d'indexation", compute="_compute_distri_in_current")
    color = fields.Integer(u"Couleur")
    total_in_current = fields.Integer(u"Total en cours", compute="_compute_total_in_current")

    @api.multi
    def _compute_recu_in_current(self):
        for rec in self:
            rec.recu_in_current = len(self.env['queue.job'].search([('channel', 'ilike', 'root.reception%'),
                                                                    ('state', '=', 'started')]))

    @api.multi
    def _compute_recu_waiting(self):
        for rec in self:
            rec.recu_waiting = len(self.env['queue.job'].search([('channel', 'ilike', 'root.reception%'),
                                                                 ('state', '=', 'pending')]))

    @api.multi
    def _compute_ident_waiting(self):
        for rec in self:
            rec.ident_waiting = len(self.env['queue.job'].search([('channel', 'ilike', 'root.identification%'),
                                                                  ('state', '=', 'pending')]))

    @api.multi
    def _compute_ident_in_current(self):
        for rec in self:
            rec.ident_in_current = len(self.env['queue.job'].search([('channel', 'ilike', 'root.identification%'),
                                                                     ('state', '=', 'started')]))

    @api.multi
    def _compute_index_waiting(self):
        for rec in self:
            rec.index_waiting = len(self.env['queue.job'].search([('channel', 'ilike', 'root.indexation%'),
                                                                  ('state', '=', 'pending')]))

    @api.multi
    def _compute_index_in_current(self):
        for rec in self:
            rec.index_in_current = len(self.env['queue.job'].search([('channel', 'ilike', 'root.indexation%'),
                                                                     ('state', '=', 'started')]))

    @api.multi
    def _compute_trt_waiting(self):
        for rec in self:
            rec.trt_waiting = len(self.env['queue.job'].search([('channel', 'ilike', 'root.traitement%'),
                                                                ('state', '=', 'pending')]))

    @api.multi
    def _compute_trt_in_current(self):
        for rec in self:
            rec.trt_in_current = len(self.env['queue.job'].search([('channel', 'ilike', 'root.traitement%'),
                                                                   ('state', '=', 'started')]))

    @api.multi
    def _compute_distri_waiting(self):
        for rec in self:
            rec.distri_waiting = len(self.env['queue.job'].search([('channel', 'ilike', 'root.distribution%'),
                                                                   ('state', '=', 'pending')]))

    @api.multi
    def _compute_distri_in_current(self):
        for rec in self:
            rec.distri_in_current = len(self.env['queue.job'].search([('channel', 'ilike', 'root.distribution%'),
                                                                      ('state', '=', 'started')]))

    @api.multi
    def _compute_total_in_current(self):
        for rec in self:
            rec.total_in_current = len(self.env['queue.job'].search([('state', '!=', 'done')]))
