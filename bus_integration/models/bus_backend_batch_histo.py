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


from openerp import models, fields, api


class BusBackendBatchHisto(models.Model):
    _name = 'bus.backend.batch.histo'

    batch_id = fields.Many2one('bus.backend.batch', string=u"Batch")
    serial_id = fields.Integer(string=u"Serial ID")
    treatment = fields.Char(u"Treatment")
    model = fields.Char(u"Model")
    export_ids = fields.Char(u"Exported ids")
    last_job_state = fields.Selection([('running', u"Running"), ('done', u"Done"), ('error', u"Error")],
                                      string=u'Last job state', compute="_compute_last_job_state")
    transfer_state = fields.Selection([('started', u"Started"), ('finished', u"Finished"), ('blocked', u"Blocked"),
                                       ('error', u"Error")], default='started', string=u"Transfer state",
                                      help=u"Set finished when return sync is ok")
    log_ids = fields.One2many('bus.backend.batch.histo.log', 'histo_id', string=u"Logs")

    @api.multi
    def _compute_last_job_state(self):
        for rec in self:
            log = self.env['bus.backend.batch.histo.log'].search([('histo_id', '=', rec.id)],
                                                                 order='create_date desc', limit=1)
            rec.last_job_state = log and log.state or False

    @api.multi
    def add_log(self, message_id, job_uuid, log=""):
        self.ensure_one()
        histo_log = self.env['bus.backend.batch.histo.log'].create({
            'histo_id': self.id,
            'message_id': message_id,
            'job_uuid': job_uuid,
            'log': log
        })
        return histo_log


class BusextendostoLog(models.Model):
    _name = 'bus.backend.batch.histo.log'

    histo_id = fields.Many2one("bus.backend.batch.histo", string=u"History")
    serial_id = fields.Integer(u"Serial ID")
    log = fields.Char(u"Log")
    job_uuid = fields.Char(string=u"Job UUID")
    state = fields.Selection([(u"running", u"Running"),
                              (u"done", u"Done"),
                              (u"error", u"Error")],
                             string=u'Status', compute='_get_job_state')
    message_id = fields.Many2one('bus.message', string=u"Message")

    @api.multi
    def _get_job_state(self):
        for rec in self:
            job = self.env['queue.job'].search([('uuid', '=', rec.job_uuid)])
            if job:
                rec.state = job.state

    @api.model
    def check_state(self):
        logs = self.search([('state', '=', 'running')])
        for log in logs:
            if log.job_uuid:
                job = self.env['queue.job'].search([('uuid', '=', log.job_uid)])
                if job.state == 'failed':
                    log.state = 'error'
                elif job.state == 'done':
                    log.state = 'done'
