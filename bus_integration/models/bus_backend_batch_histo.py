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
    name = fields.Char(u"Treatment")
    state = fields.Selection([(u"running", u"En Cours"),
                              (u"done", u"Réussi"),
                              (u"error", u"Erreur")],
                             string=u'Statut', compute="_compute_last_statut")

    @api.multi
    def _compute_last_statut(self):
        for rec in self:
            histo = self.env['bus.backend.batch.histo.log'].search([('histo_id', '=', rec.id)],
                                                                   order='create_date desc', limit=1)
            rec.state = histo and histo.state or False

    @api.model
    def create_histo_if_needed(self, message_dict):
        serial_id = message_dict.get('header', {}).get('serial_id')
        histo = self.search([('serial_id', '=', serial_id)], limit=1)
        if histo:
            histo_logs = self.env['bus.backend.batch.histo.log'].search([('serial_id', '=', serial_id)])
            histo_logs.write({'state': 'done'})
        else:
            histo = self.env['bus.backend.batch.histo'].create({
                'serial_id': serial_id,
                'name': u"%s : %s > %s - %s" % (serial_id,
                                                message_dict.get('header').get('origin'),
                                                message_dict.get('header').get('dest'),
                                                message_dict.get('header').get('treatment')),
                'state': 'running'
            })
        return histo


class BusextendostoLog(models.Model):
    _name = 'bus.backend.batch.histo.log'

    histo_id = fields.Many2one("bus.backend.batch.histo", string=u"History")
    serial_id = fields.Integer(u"Serial ID")
    log = fields.Char(u"Log")
    job_uid = fields.Char(string=u"Job UUID")
    state = fields.Selection([(u"running", u"Running"),
                              (u"done", u"Done"),
                              (u"error", u"Error")],
                             string=u'Status')

    @api.model
    def check_state(self):
        logs = self.search([('state', '=', 'running')])
        for log in logs:
            if log.job_uid:
                job = self.env['queue.job'].search([('uuid', '=', log.job_uid)])
                if job.state == 'failed':
                    log.state = 'error'
                elif job.state == 'done':
                    log.state = 'done'
