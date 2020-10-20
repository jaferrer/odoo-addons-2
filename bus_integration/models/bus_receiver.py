# -*- coding: utf8 -*-

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
from datetime import datetime
from openerp import models, api, exceptions
from openerp.addons.connector.session import ConnectorSession
from ..connector.jobs import job_receive_message


class BusSynchronizationReceiver(models.AbstractModel):
    _name = 'bus.receiver'

    @api.model
    def receive_message(self, code, message_json, jobify=True):
        try:
            backend = self.env['bus.configuration'].search([('code', '=', code)])
            if not backend:
                raise exceptions.ValidationError(u"No bakcend found : %s" % code)
            dict_message = json.loads(message_json, encoding='utf-8')

            # search for a parent message id
            #     1. look for a sent message with the same cross id origin (ex : master:1>master:3)
            #     2. look for a sent message in the upper level of cross id origin (ex: master:1)

            parent_message = self.env['bus.message'].get_same_cross_id_messages(dict_message)._get_first_sent_message()
            if not parent_message:
                parent_message = self.env['bus.message'].get_parent_cross_id_messages(dict_message)\
                    ._get_first_sent_message()
            parent_message_id = parent_message.id if parent_message else False
            message = self.env['bus.message'].create_message(dict_message, 'received', backend, parent_message_id)
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
    def process_received_message(self, message_id, previous_post_demand=None):
        new_post_demand = previous_post_demand if previous_post_demand else {}
        message = self.env['bus.message'].browse(message_id)
        result = True
        new_msg = False
        # synchronisation request | dependency response
        if message.treatment in ['SYNCHRONIZATION', 'DEPENDENCY_SYNCHRONIZATION']:
            result, demand, post_demand = self.env['bus.importer'].import_synchronization_message(message_id)
            new_post_demand.update(post_demand)
            if demand:
                self.env['bus.exporter'].send_dependancy_synchronization_demand(message_id, demand)
            else:
                new_msg = self.env['bus.exporter'].send_synchro_return_message(message_id, result)
                if new_msg and not new_msg.is_error() and message.cross_id_origin_parent_id:  # replays parent message
                    self.process_received_message(message.get_parent().id, new_post_demand)
                elif new_msg and not new_msg.is_error() and new_post_demand and not message.cross_id_origin_parent_id:
                    self.env['bus.exporter'].send_post_dependancy_synchronization_demand(
                        parent_message_id=message_id, demand=new_post_demand)

        # dependency request
        elif message.treatment in ['DEPENDENCY_DEMAND_SYNCHRONIZATION']:
            self.env['bus.exporter'].send_dependency_synchronization_response(message_id)
        elif message.treatment in ['POST_DEPENDENCY_DEMAND_SYNCHRONIZATION']:
            self.env['bus.exporter'].send_post_dependency_synchronization_response(message_id)
        # synchronisation response
        elif message.treatment == 'SYNCHRONIZATION_RETURN':
            self.register_synchro_return(message_id)
        # deletion request
        elif message.treatment == 'DELETION_SYNCHRONIZATION':
            message_dict = self.env['bus.importer'].import_deletion_synchronization_message(message_id)
            self.env['bus.exporter'].send_deletion_return_message(message_id, message_dict)
        # restrict ids request
        elif message.treatment == 'RESTRICT_IDS_SYNCHRONIZATION':
            message_dict = self.env['bus.importer'].run_synchro_restrict_ids(message)
            new_msg = self.env['bus.exporter'].send_restrict_id_response(message, message_dict)
        # deletion response
        elif message.treatment == 'DELETION_SYNCHRONIZATION_RETURN':
            self.env['bus.importer'].register_synchro_deletion_return(message_id)
        elif message.treatment in ['CHECK_SYNCHRONIZATION_RETURN']:
            self.env['bus.importer'].register_synchro_check_return(message_id)
        elif message.treatment == 'BUS_SYNCHRONIZATION_RETURN':
            self.env['bus.importer'].register_synchro_bus_response(message)
        elif message.treatment == 'RESTRICT_IDS_SYNCHRONIZATION_RETURN':
            self.env['bus.importer'].register_synchro_restrict_ids_return(message)
        else:
            result = False
        if not result:
            return False
        successful_treatments = ('SYNCHRONIZATION_RETURN',
                                 'DELETION_SYNCHRONIZATION_RETURN',
                                 'BUS_SYNCHRONIZATION_RETURN',
                                 'RESTRICT_IDS_SYNCHRONIZATION_RETURN')
        if (message.treatment in successful_treatments) or (new_msg and new_msg.treatment in successful_treatments):
            date_done = datetime.now()
            linked_msgs = message.get_same_cross_id_messages(json.loads(message.message))
            for msg in linked_msgs:
                msg.write({'date_done': date_done})
        return result

    @api.model
    def register_synchro_return(self, message_id):
        message = self.env['bus.message'].browse(message_id)
        message_dict = json.loads(message.message)
        return_res = message_dict.get('body', {}).get('return', {})
        result = return_res.get('result', False)
        return_state = return_res.get('state', False)
        message.result = 'error' if not return_state else 'finished'
        self.env['bus.importer'].import_bus_references(message, result, return_state)
        return False
