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
import datetime as dt
from openerp import tools

from openerp import models, fields, api

_logger = logging.getLogger(__name__)

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


@job(default_channel='root.distribution.local')
def traitement_distri_local(session, model_name, distri_id, archive, archive_id):
    try:
        distri = session.pool[model_name].browse(session.cr, session.uid, distri_id)
        archive_msg = session.pool["archive"].browse(session.cr, session.uid, archive_id)
        param = session.env[distri.type_id.model_param_name].search([('distributeur_id',
                                                                      '=',
                                                                      distri_id)])[0]

        if not param.directory_path:
            archive_msg.create_log({
                'archive_id': archive_msg.id,
                'state': 'ERROR',
                'log': u"Aucun répertoire sur %s" % (distri.name)
            })
            return "OK"

        target = param.directory_path

        filedate = dt.datetime.now().strftime('%Y%m%d%H%M%S')

        filename = '%s_%s.%s' % (filedate, archive_id, param.extension)

        targetfile = '%s/%s' % (target, filename)
        with open(targetfile, 'w') as awa_file:
            awa_file.write(tools.ustr(archive, errors='replace'))

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
    def push_local(self, archive, archive_id):
        _logger.info('Start creation of the file on the local')
        new_ctx = dict(self.env.context)
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)

        traitement_distri_local.delay(
            session, 'distributeur', self.id,
            archive, archive_id, priority=3
        )
        return True


class ConnectorTypeLocalParameter(models.Model):
    _name = 'connector.type.distri.local.parameter'

    directory_path = fields.Char(string=u'Chemin', default=".")
    extension = fields.Char(string=u'extension de fichier', default="txt")

    distributeur_id = fields.Many2one('distributeur', string=u"Distributeur", required=True)
