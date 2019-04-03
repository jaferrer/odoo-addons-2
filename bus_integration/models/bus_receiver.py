# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from datetime import datetime
from openerp import models, api, exceptions
from openerp.addons.connector.session import ConnectorSession
from ..connector.jobs import job_receive_message


class BusSynchronizationReceiver(models.AbstractModel):
    _name = 'bus.receiver'

    @api.model
    def receive_message(self, code, message_json, jobify=True):
        try:
            backend = self.env['bus.backend'].search([('code', '=', code)])
            if not backend:
                raise exceptions.ValidationError(u"No bakcend found : %s" % code)
            dict_message = json.loads(message_json, encoding='utf-8')
            message = self.env['bus.message'].create_message(dict_message, 'received', backend.id)
            if jobify:
                job_uiid = job_receive_message.delay(ConnectorSession.from_env(self.env), self._name, message.id)
            else:
                job_uiid = job_receive_message(ConnectorSession.from_env(self.env), self._name, message.id)
            result = u"Receive Message : %s in processing by the job %s" % (message.id, job_uiid)
            to_raise = False
        except exceptions.ValidationError as error:
            result = error
            to_raise = True
        except AttributeError as error:
            result = error
            to_raise = True
        except TypeError as error:
            result = error
            to_raise = True
        if to_raise:
            raise exceptions.except_orm(u"Reception Error", result)
        return result

    @api.model
    def process_received_message(self, message_id):
        message = self.env['bus.message'].browse(message_id)
        result = True
        if message.treatment in ['SYNCHRONIZATION', 'DEPENDENCY_SYNCHRONIZATION']:
            result, demand = self.env['bus.importer'].import_synchronization_message(message_id)
            if demand:
                self.env['bus.exporter'].send_dependancy_demand(message_id, demand)
            else:
                self.env['bus.exporter'].send_synchro_return_message(message_id, result)
        elif message.treatment == 'DEPENDENCY_DEMAND_SYNCHRONIZATION':
            self.env['bus.exporter'].send_dependency_demand_message(message_id)
        elif message.treatment == 'SYNCHRONIZATION_RETURN':
            self.register_synchro_return(message_id)
        elif message.treatment == 'DELETION_SYNCHRONIZATION':
            result = self.env['bus.importer'].import_deletion_synchronization_message(message_id)
            self.env['bus.exporter'].send_deletion_return_message(message_id, result)
        elif message.treatment == 'DELETION_SYNCHRONIZATION_RETURN':
            self.env['bus.importer'].register_synchro_deletion_return(message_id)
        else:
            result = False
        message.write({'done': result, 'date_done': datetime.now()})
        return result

    @api.model
    def register_synchro_return(self, message_id):
        # TODO : To implement
        pass
