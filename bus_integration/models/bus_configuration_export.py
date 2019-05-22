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

from openerp import models, fields, api


class BusConfigurationExport(models.Model):
    _name = 'bus.configuration.export'
    _order = 'dependency_level ASC, model ASC'

    name = fields.Char(u"Name", required=True, compute="_compute_name")
    configuration_id = fields.Many2one('bus.configuration', string=u"Backend",
                                       default=lambda self: self.env['bus.configuration'].search([])[0])
    recipient_id = fields.Many2one('bus.base', string=u"Recipient")
    bus_username = fields.Char(u"BUS user name", related='recipient_id.bus_username', readonly=True, store=True)
    model = fields.Char(u"Model", required=True)
    bus_reception_treatment = fields.Selection([('simple_reception', u"Simple reception"),
                                                ('check_reception', u"Check reception")],
                                               u"Treatment in BUS database", default='simple_reception', required=True)
    treatment_type = fields.Selection([('SYNCHRONIZATION', u"Synchronization"),
                                       ('DELETION_SYNCHRONIZATION', u"Deletion"),
                                       ('CHECK_SYNCHRONIZATION', u"Check")],
                                      string=u"Treatment type", default='SYNCHRONIZATION', required=True)
    cron_created = fields.Boolean(u"Cron created", compute='_get_cron')
    cron_active = fields.Boolean(u"Cron active", compute='_get_cron')
    last_transfer_state = fields.Selection([('never_processed', u"Never processed"),
                                            ('started', u"Started"),
                                            ('finished', u"Finished"),
                                            ('blocked', u"Blocked"),
                                            ('error', u"Error")],
                                           string=u'Last transfer status', compute="_compute_last_transfer")
    last_transfer_id = fields.Many2one('bus.configuration.export.histo', string=u"Last transfer",
                                       compute='_compute_last_transfer')
    serial_id = fields.Integer(u"Serial")
    chunk_size = fields.Integer(u"Export chunk size")
    domain = fields.Char(u"Domain", required=True, default="[]", help=u"""
        You can see the additional object/functions in the model bus.configuration.export.
        You can acces to : relativedelta, self, context.
        For datetime use shorcut date, date_to_str to translate dates.
        last_send_date to get the last date of dispatch.""")
    mapping_object_id = fields.Many2one('bus.object.mapping', u"Mapping", compute='_get_mapping_object', store=True)
    dependency_level = fields.Integer(u"Dependency level", related='mapping_object_id.dependency_level', store=True)
    bach_histo_ids = fields.One2many('bus.configuration.export.histo', 'bus_configuration_export_id',
                                     string=u"Batch history")

    @api.multi
    @api.depends('model')
    def _get_mapping_object(self):
        for rec in self:
            mapping = self.env['bus.object.mapping'].search([('model_name', '=', rec.model)])
            rec.mapping_object_id = mapping

    @api.multi
    @api.depends('recipient_id', 'model', 'domain')
    def _compute_name(self):
        for rec in self:
            rec.name = u"%s%s→%s" % (
                rec.model or "[_]",
                "" if rec.domain == "[]" else "[...]",
                rec.recipient_id.display_name or "[_]")

    @api.multi
    def _compute_last_transfer(self):
        for rec in self:
            histo = self.env['bus.configuration.export.histo'].search([('serial_id', '=', rec.serial_id)],
                                                                      order="create_date desc", limit=1)
            rec.last_transfer_id = histo
            rec.last_transfer_state = histo and histo.transfer_state or 'never_processed'

    @api.multi
    def run_batch(self):
        self.ensure_one()
        return self.env['bus.exporter'].run_export(self.id)

    @api.multi
    def create_cron(self):
        self.write({
            'cron_created': True
        })
        item = {
            'bus_configuration_export_id': self.id,
            'name': u"batch d'export de type : %s -- > de %s pour %s --" % (self.display_name,
                                                                            self.configuration_id.sender_id.name,
                                                                            self.recipient_id.name),
            'user_id': 1,
            'priority': 100,
            'interval_type': 'days',
            'interval_number': 1,
            'numbercall': -1,
            'doall': False,
            'model': 'bus.configuration.export',
            'function': 'export_message_synchro',
            'args': "(%s)" % repr([self.id]),
            'active': True
        }
        cron = self.env['ir.cron'].create(item)
        return cron

    @api.multi
    def edit_cron(self):
        self.ensure_one()
        cron = self.env['ir.cron'].search(['&', ('bus_configuration_export_id', '=', self.id),
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
    def _get_cron(self):
        for rec in self:
            cron = self.env['ir.cron'].search([('bus_configuration_export_id', '=', rec.id)], limit=1)
            rec.cron_created = cron
            rec.cron_active = cron and cron.active or False

    @api.multi
    def get_serial(self, export_ids):
        histo = self.env["bus.configuration.export.histo"].create({
            'bus_configuration_export_id': self.id,
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
        return self.last_transfer_id and self.last_transfer_id.write_date or fields.Datetime\
            .to_string(datetime.strptime('1900', '%Y'))
