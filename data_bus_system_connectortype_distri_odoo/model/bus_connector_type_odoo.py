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

import logging
import jsonrpclib
import socket
import json

from openerp import models, fields, api
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import FailedJobError

_logger = logging.getLogger(__name__)


@job(default_channel='root.distribution')
def traitement_distri_odoo(session, model_name, distri_id, archive, archive_id):
    try:
        distri = session.pool[model_name].browse(session.cr, session.uid, distri_id)
        archive_msg = session.pool["archive"].browse(session.cr, session.uid, archive_id)
        param = session.env[distri.type_id.model_param_name].search([('distributeur_id',
                                                                      '=',
                                                                      distri_id)])[0]

        if not param.url:
            archive_msg.create_log({
                'archive_id': archive_msg.id,
                'state': 'ERROR',
                'log': u"Aucune url sur %s" % (distri.name)
            })
            return "OK"

        tuple_result = param.test_connexion(raise_error=True)
        args = [param.db, tuple_result[1], param.pwd, param.model_name, param.method_name, archive]
        _call_object_execute(tuple_result[0], args)

        archive_msg.create_log({
            'archive_id': archive_msg.id,
            'state': 'DISTRIBUE',
            'log': u"Distribué à %s" % (distri.name)
        })
        return "OK"
    except Exception as e:
        archive_msg = session.pool["archive"].browse(session.cr, session.uid, archive_id)
        archive_msg.create_log({
            'archive_id': archive_msg.id,
            'state': 'ERROR',
            'log': e.message
        })


class Recepteur(models.Model):
    _inherit = 'distributeur'

    @api.multi
    def push_odoo(self, archive, archive_id):
        _logger.info('Start creation of the file on the local')
        new_ctx = dict(self.env.context)
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)

        traitement_distri_odoo.delay(
            session, 'distributeur', self.id,
            archive, archive_id, priority=3
        )
        return True


class ConnectorTypeOdooParameter(models.Model):
    _name = 'connector.type.distri.odoo.parameter'

    url = fields.Char(string=u'url')
    login = fields.Char(string=u'login')
    pwd = fields.Char(string=u'mdp de fichier')
    db = fields.Char(string=u'Base de données')
    port = fields.Integer(string=u'port')
    model_name = fields.Char(string=u'Model destinataire')
    method_name = fields.Char(string=u'Méthode destinataire')

    distributeur_id = fields.Many2one('distributeur', string=u"Distributeur", required=True)

    connexion_state = fields.Char(string="Etat de la connexion", compute='test_connexion', store=False)

    @api.multi
    def test_connexion(self, context=None, raise_error=False):
        self.ensure_one()
        url = "http://%s:%s/jsonrpc" % (self.url, self.port)
        server = jsonrpclib.Server(url)
        # log in the given database

        result = 0

        try:
            result = server.call(service="common", method="login", args=[self.db, self.login, self.pwd])
            self.connexion_state = "Erreur Login/MdP" if result == 0 else "OK"
        except socket.error as e:
            self.connexion_state = e.strerror
        except jsonrpclib.ProtocolError:
            self.connexion_state = _return_last_jsonrpclib_error()

        if raise_error and self.connexion_state != "OK":
            raise FailedJobError(self.connexion_state)

        return (server, result)

    @api.multi
    def recompute_connexion_state(self):
        return {
            'name': 'Parameter',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'flags': {'form': {'action_buttons': True}},
            'res_id': self.id,
            'target': 'new'
        }


def _return_last_jsonrpclib_error():
    return json.loads(jsonrpclib.history.response).get('error').get('data').get('message')


def _call_object_execute(server, args):
    try:
        server.call(service="object", method="execute", args=args)
    except jsonrpclib.ProtocolError:
        raise FailedJobError(_return_last_jsonrpclib_error())
