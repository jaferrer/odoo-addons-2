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
import os, glob

from openerp import models, fields, api

_logger = logging.getLogger(__name__)

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession


@job(default_channel='root.reception.local')
def traitement_reception_local(session, model_name, recepteur_id, archive, archive_id):
    recep = session.pool[model_name].browse(session.cr, session.uid, recepteur_id)
    recep.exec_recep_seq(archive, archive_id, state="IDENT")
    return "OK"


class Recepteur(models.Model):
    _inherit = 'recepteur'

    @api.multi
    def pull_local(self):
        _logger.info('Start creation of the file on the local')
        param = self.env[self.type_id.model_param_name].search([('recep_id', '=', self.id)])[0]
        target = param.path

        scanfiles = [file_local for file_local in glob.glob("%s/%s" % (target, param.file_reg)) if os.path.isfile(file_local)]
        _logger.debug('%s files: %s', target, scanfiles)

        new_ctx = dict(self.env.context)
        session = ConnectorSession(self.env.cr, self.env.uid,
                                   context=new_ctx)

        for fich in scanfiles:
            filepath = fich
            with open(filepath, 'r') as file_read:
                str = file_read.read()
                archive_id = self.env['archive'].create({
                    'message': str,
                    'recep_id': self.id,
                    'message_name': fich,
                    'type_message_id': self.env.ref('data_bus_system_backend.message_inconnu').id
                })
                archive_id.create_log({
                    'archive_id': archive_id.id,
                    'state': 'RECU'
                })
                traitement_reception_local.delay(
                    session, 'recepteur', self.id,
                    str, archive_id.id, priority=3
                )
            os.remove(filepath)
        return True


class ConnectorTypeLocalParameter(models.Model):
    _name = 'connector.type.recep.local.parameter'

    path = fields.Char(string=u'archive path')
    file_reg = fields.Char(string=u'regex', default="*")

    recep_id = fields.Many2one('recepteur', string=u"Recepteur", required=True)