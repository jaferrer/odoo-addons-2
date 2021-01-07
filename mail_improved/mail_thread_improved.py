# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp import models, api, fields


_logger = logging.getLogger(__name__)


@job
def job_launch_useless_messages_deletion(session, model_name, context):
    session.env[model_name].with_context(context).launch_useless_messages_deletion()
    return "End of deletion"


@job(default_channel='root.mail_message_cleaner_chunk')
def job_delete_useless_message_for_model(session, model_name, model, context):
    session.env[model_name].with_context(context).launch_useless_messages_deletion_for_model(model)
    return "deleted chunck of %s" % model_name


class MailThreadImprovedModels(models.Model):
    _inherit = 'mail.message'

    code = fields.Char(string=u"Code", readonly=True, copy=False)

    @api.model
    def compute_models_to_process(self):
        self.env.cr.execute("""SELECT DISTINCT model FROM mail_message""")
        res = [item[0] for item in self.env.cr.fetchall() if item[0]]
        return res

    @api.model
    def cron_launch_useless_messages_deletion(self):
        job_launch_useless_messages_deletion.delay(ConnectorSession.from_env(self.env), 'mail.message',
                                                   dict(self.env.context),
                                                   description=u"Deleting useless messages")

    @api.model
    def launch_useless_messages_deletion(self):
        models_list = self.compute_models_to_process()
        for model in models_list:
            job_delete_useless_message_for_model\
                .delay(ConnectorSession.from_env(self.env),
                       'mail.message',
                       model,
                       dict(self.env.context),
                       description=u"Poping job to delete unused chunk of mail.message for %s" % model,
                       priority=100, )

    @api.model
    def launch_useless_messages_deletion_for_model(self, model):
        chunck_size = 100
        try:
            table_name = self.env[model]._table
        except KeyError:
            return  # in the case some model have been removed by an update
        req = """SELECT id FROM mail_message
                WHERE model = '%s' AND
                      NOT exists(SELECT 1
                                 FROM %s current_table
                                 WHERE current_table.id = mail_message.res_id)
                 LIMIT %s;"""
        self.env.cr.execute(req % (model, table_name, chunck_size))
        res = self.env.cr.fetchall()
        msg_to_delete_ids = res and reduce(lambda x, y: x + y, res)
        _logger.debug("=== useless_messages_deletion_for_model %s deleting %s", model, msg_to_delete_ids)
        if msg_to_delete_ids:
            del_req = """DELETE FROM mail_message WHERE id IN %s"""
            self.env.cr.execute(del_req, (msg_to_delete_ids,))
            # we launch again the same job to handle the next chunck, it will return doing nothing if no more msg
            job_delete_useless_message_for_model\
                .delay(ConnectorSession.from_env(self.env),
                       'mail.message',
                       model,
                       dict(self.env.context),
                       description=u"Poping job to delete chunk of unused mail.message for %s" % model,
                       priority=100,)

    @api.model
    def create(self, vals):
        vals['code'] = self.env.context.get('message_code', '')
        return super(MailThreadImprovedModels, self).create(vals)
