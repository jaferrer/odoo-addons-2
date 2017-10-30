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
import datetime as dt
from openerp import tools

from openerp import models, fields, api

_logger = logging.getLogger(__name__)

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


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

        url = "http://%s:%s/jsonrpc" % (param.url, param.port)

        server = jsonrpclib.Server(url)

        # log in the given database
        uid = server.call(service="common", method="login", args=[param.db, param.login, param.pwd])

        args = [param.db, uid, param.pwd, param.model_name, param.method_name, archive]
        server.call(service="object", method="execute", args=args)

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
