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

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

from openerp import models, api, fields


@job
def job_launch_useless_messages_deletion(session, model_name, context):
    session.env[model_name].with_context(context).launch_useless_messages_deletion()
    return "End of deletion"


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
            table_name = self.env[model]._table
            self.env.cr.execute("""DELETE FROM mail_message
WHERE model = '%s' AND
      NOT exists(SELECT 1
                 FROM %s current_table
                 WHERE current_table.id = mail_message.res_id);""" % (model, table_name,))

    @api.model
    def create(self, vals):
        vals['code'] = self.env.context.get('message_code', '')
        return super(MailThreadImprovedModels, self).create(vals)
