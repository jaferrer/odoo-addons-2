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

from datetime import datetime
from dateutil import relativedelta

from openerp import models, fields, api, exceptions


class BusextendBackendBatch(models.Model):
    _name = 'bus.backend.batch'

    name = fields.Char(u"Name", required=True)
    backend_id = fields.Many2one('bus.backend', string=u"Backend")
    recipient_id = fields.Many2one('res.partner', string=u"Recipient")
    bus_username = fields.Char(u"BUS user name", related='recipient_id.bus_username', readonly=True, store=True)
    model = fields.Char(u"Model")
    bus_reception_treatment = fields.Selection([('simple_reception', u"Simple reception")],
                                               u"Treatment in BUS database", required=True)
    treatment_type = fields.Selection([('SYNCHRONIZATION', u"Synchronization"),
                                       ('DELETION_SYNCHRONIZATION', u"Deletion")],
                                      string=u"Treatment type", required=True)
    init_conf = fields.Boolean(u"Init conf")
    last_transfer_state = fields.Selection([('never_processed', u"Never processed"),
                                            ('started', u"Started"),
                                            ('finished', u"Finished"),
                                            ('blocked', u"Blocked"),
                                            ('error', u"Error")],
                                           string=u'Last transfer status', compute="_compute_last_transfer_state")
    serial_id = fields.Integer(u"Serial")
    chunk = fields.Integer(u"Export chunk size")
    domain = fields.Char(u"Domain", required=True, help=u"""
        You can see the additional object/functions in the model bus.backend.batch.
        You can acces to : relativedelta, self, context.
        For datetime use shorcut date, date_to_str to translate dates.
        last_send_date to get the last date of dispatch.""")

    bach_histo_ids = fields.One2many('bus.backend.batch.histo', 'batch_id', string=u"Batch history")

    @api.multi
    def _compute_last_transfer_state(self):
        for rec in self:
            histo = self.env['bus.backend.batch.histo'].search([('serial_id', '=', rec.serial_id)],
                                                               order="create_date desc", limit=1)
            rec.last_transfer_state = histo and histo.transfer_state or 'never_processed'

    @api.multi
    def run_batch(self):
        self.ensure_one()
        if self.treatment_type == 'SYNCHRONIZATION':
            return self.env['bus.exporter'].run_export(self.id)
        if self.treatment_type == 'DELETION_SYNCHRONIZATION':
            return self.env['bus.exporter'].run_export(self.id, deletion=True)
        raise exceptions.ValidationError(u"No treatment Found")

    @api.multi
    def create_cron(self):
        self.write({
            'init_conf': True
        })
        item = {
            'bus_bakend_id': self.id,
            'name': u"batch d'export de type : %s -- > de %s pour %s --" % (self.display_name,
                                                                            self.backend_id.sender_id.name,
                                                                            self.recipient_id.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'days',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': 'bus.backend.batch',
            'function': 'export_message_synchro',
            'args': "(%s)" % repr([self.id]),
            'active': True
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(['&', ('bus_bakend_id', '=', self.id),
                                           '|', ('active', '=', False), ('active', '=', True)])
        if not cron:
            cron = self._create_cron()
        return {
            'name': u"Cron",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ir.cron',
            'res_id': cron.id,
            'context': False
        }

    @api.multi
    def get_serial(self, export_ids):
        histo = self.env["bus.backend.batch.histo"].create({
            'batch_id': self.id,
            'treatment': self.treatment_type,
            'model': self.model,
            'export_ids': export_ids,
        })
        histo.serial_id = histo.id
        self.serial_id = histo.id
        return histo

    @api.multi
    def export_domain_keywords(self):
        self.ensure_one()
        return {
            'date': datetime,
            'relativedelta': relativedelta.relativedelta,
            'self': self,
            'context': self.env.context,
            'date_to_str': fields.Date.to_string,
            'last_send_date': self.get_last_send_date()
        }

    @api.multi
    def get_last_send_date(self):
        self.ensure_one()
        histo = self.env['bus.backend.batch.histo'].search([('batch_id', '=', self.id)], order='create_date DESC',
                                                           limit=1)
        log = self.env['bus.backend.batch.histo.log'].search([('histo_id', '=', histo.id)],
                                                             order='create_date DESC', limit=1)
        return log.create_date
