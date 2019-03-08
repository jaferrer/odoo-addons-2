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


class BusextendHisto(models.Model):
    _name = 'busextend.backend.batch.histo'

    batch_id = fields.Many2one("busextend.backend.batch", string="Batch")
    serial_id = fields.Integer(string="Serial ID")
    name = fields.Char('traitement')
    state = fields.Selection([(u"INPROGRESS", u"En Cours"),
                              (u"DONE", u"Réussi"),
                              (u"ERROR", u"Erreur")],
                             string=u'Statut', compute="_compute_last_statut")

    @api.multi
    def _compute_last_statut(self):
        for rec in self:
            histo = self.env['busextend.backend.batch.histo.log'].search(
                [('histo_id', '=', rec.id)], order="create_date desc", limit=1)
            if histo:
                rec.state = histo.state


class BusextendostoLog(models.Model):
    _name = 'busextend.backend.batch.histo.log'

    histo_id = fields.Many2one("busextend.backend.batch.histo", string="historique")
    serial_id = fields.Integer(string="Serial ID")
    log = fields.Char('log')
    job_uid = fields.Char(string="Job")
    state = fields.Selection([(u"INPROGRESS", u"En Cours"),
                              (u"DONE", u"Réussi"),
                              (u"ERROR", u"Erreur")],
                             string=u'Statut')

    @api.model
    def check_state(self):
        logs = self.search([('state', '=', 'INPROGRESS')])
        for log in logs:
            if log.job_uid:
                job = self.env['queue.job'].search([('uuid', '=', log.job_uid)])
                if job.state == 'failed':
                    log.state = 'ERROR'
                elif job.state == 'done':
                    log.state = 'DONE'
