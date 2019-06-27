# -*- coding: utf8 -*-
#
# Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields, exceptions


class JobMonitoring(models.Model):
    _name = 'job.monitoring'
    _order = 'sequence asc'

    name = fields.Char(u"Name")
    res_model = fields.Char(u"Model")
    domain = fields.Char(u"Domain")
    channel = fields.Char(u"Channel of queue jobs")
    sequence = fields.Integer(u"Sequence")
    nb_started_jobs = fields.Integer(u"Started jobs", compute='_compute_jobs')
    nb_pending_jobs = fields.Integer(u"Pending jobs", compute='_compute_jobs')
    nb_enqueued_jobs = fields.Integer(u"Enqueued jobs", compute='_compute_jobs')
    nb_inprogress_jobs = fields.Integer(u"Enqueued jobs", compute='_compute_jobs')
    nb_done_jobs = fields.Integer(u"Done jobs", compute='_compute_jobs')
    nb_error_jobs = fields.Integer(u"Error jobs", compute='_compute_jobs')
    nb_total_jobs = fields.Integer(u"Total jobs", compute='_compute_jobs')
    rate_started = fields.Integer(u"Rate started", compute='_compute_jobs')
    rate_pending = fields.Integer(u"Rate pending", compute='_compute_jobs')
    rate_enqueued = fields.Integer(u"Rate enqueued", compute='_compute_jobs')
    rate_done = fields.Integer(u"Rate done", compute='_compute_jobs')
    rate_error = fields.Integer(u"Rate error", compute='_compute_jobs')
    color = fields.Integer(u"Color")

    @api.multi
    def _compute_jobs(self):
        for rec in self:
            default_domain = ('channel', '=', rec.channel)
            job_model = self.env['queue.job']
            rec.nb_total_jobs = len(job_model.search([default_domain]))
            rec.nb_started_jobs = len(job_model.search([default_domain, ('state', '=', 'started')]))
            rec.nb_pending_jobs = len(job_model.search([default_domain, ('state', '=', 'pending')]))
            rec.nb_enqueued_jobs = len(job_model.search([default_domain, ('state', '=', 'enqueued')]))
            rec.nb_inprogress_jobs = len(job_model.search([default_domain, ('state', 'in',
                                                                            ['pending', 'enqueued', 'started'])]))
            rec.nb_done_jobs = len(job_model.search([default_domain, ('state', '=', 'done')]))
            rec.nb_error_jobs = len(job_model.search([default_domain, ('state', '=', 'failed')]))
            if rec.nb_inprogress_jobs:
                rec.rate_started = (rec.nb_started_jobs / float(rec.nb_inprogress_jobs)) * 100
                rec.rate_pending = (rec.nb_pending_jobs / float(rec.nb_inprogress_jobs)) * 100
                rec.rate_enqueued = (rec.nb_enqueued_jobs / float(rec.nb_inprogress_jobs)) * 100
            else:
                rec.rate_started = 0
                rec.rate_pending = 0
                rec.rate_enqueued = 0
            if rec.nb_total_jobs:
                rec.rate_done = (rec.nb_done_jobs / float(rec.nb_total_jobs)) * 100
                rec.rate_error = (rec.nb_error_jobs / float(rec.nb_total_jobs)) * 100
            else:
                rec.rate_done = 0
                rec.rate_error = 0

    @api.multi
    def view_jobs(self):
        self.ensure_one()
        return {
            'name': u"Job of channel : %s" % self.channel,
            'type': 'ir.actions.act_window',
            'res_model': 'queue.job',
            'view_mode': 'tree,form',
            'domain': [('channel', '=', self.channel)]
        }

    @api.multi
    def view_datas(self):
        self.ensure_one()
        if not self.res_model:
            raise exceptions.ValidationError(u"No model defined")
        return {
            'name': u"Job of channel : %s" % self.channel,
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'view_mode': 'tree,form',
            'domain': self.domain or []
        }
