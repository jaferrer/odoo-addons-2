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

from datetime import datetime, timedelta
from dateutil import relativedelta

from openerp import models, fields, api
from openerp.addons.base.ir.ir_cron import _intervalTypes


class BusConfigurationExport(models.Model):
    _name = 'bus.configuration.export'
    _order = 'model ASC'

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
                                       ('RESTRICT_IDS_SYNCHRONIZATION', u"Restrict ids"),
                                       ('CHECK_SYNCHRONIZATION', u"Check"),
                                       ('BUS_SYNCHRONIZATION', u"Bus")],
                                      string=u"Treatment type", default='SYNCHRONIZATION', required=True)
    last_transfer_state = fields.Selection([('never_processed', u"Never processed"),
                                            ('inprogress', u"In progress"), ('error', u"Error"), ('done', u"Done")],
                                           string=u'Last transfer status', compute="_compute_last_transfer")
    last_transfer_id = fields.Many2one('bus.message', string=u"Last message",
                                       compute='_compute_last_transfer')
    chunk_size = fields.Integer(u"Export chunk size")
    domain = fields.Char(u"Domain", required=True, default="[]", help=u"""
        You can see the additional object/functions in the model bus.configuration.export.
        You can acces to : relativedelta, self, context.
        For datetime use shorcut date, date_to_str to translate dates.
        last_send_date to get the last date of dispatch.""")
    comment = fields.Char(u"Comment")
    mapping_object_id = fields.Many2one('bus.object.mapping', u"Mapping", compute='_get_mapping_object', store=True)
    sequence = fields.Integer(u"sequence", help=u"Order to launch export", default=99)
    dependency_level = fields.Integer(u"Dependency level", related='mapping_object_id.dependency_level', store=True,
                                      readonly=True)
    bus_message_ids = fields.One2many('bus.message', 'batch_id', string=u"Messages")
    nb_messages = fields.Integer(string=u"Nb Messages", compute='_compute_nb_messages')
    cron_sync_all = fields.Many2one('ir.cron', compute="_compute_cron")
    cron_sync_diff = fields.Many2one('ir.cron', compute="_compute_cron")
    active = fields.Boolean(u"Active", related='recipient_id.active', store=True)

    def _compute_nb_messages(self):
        for rec in self:
            rec.nb_messages = len(rec.bus_message_ids)

    @api.multi
    def view_messages(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'bus.message',
            'target': 'current',
            'domain': [('id', 'in', self.bus_message_ids.ids)]
        }

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
                "" if not rec.comment else " (%s)" % rec.comment,
                rec.recipient_id.display_name or "[_]")

    @api.multi
    def _compute_last_transfer(self):
        for rec in self:
            message = self.env['bus.message'].search([('batch_id', '=', rec.id)], order="create_date desc", limit=1)
            rec.last_transfer_id = message
            rec.last_transfer_state = message and message.result_state or 'never_processed'

    @api.multi
    def _compute_cron(self):
        """  compute local fields cron_sync_all & cron_sync_diff """
        env_ir_cron = self.env['ir.cron']
        for rec in self:
            rec.cron_sync_all = env_ir_cron \
                .with_context(active_test=False) \
                .search([('bus_configuration_export_id', '=', rec.id)], limit=1)
            rec.cron_sync_diff = env_ir_cron \
                .with_context(active_test=False) \
                .search([('bus_configuration_export_diff_id', '=', rec.id)], limit=1)

    @api.multi
    def sync_all(self):
        """ run the batch, exports all self.model's records matching self.domain"""
        self.ensure_one()
        self.env['bus.exporter'].run_export(self.id)

    @api.multi
    def sync_diff(self):
        """ run the batch, exports all self.model's records matching self.domain and created or update
        since the last last export"""
        force_domain = "[('write_date', '>', last_send_date)]"
        job_uuids = {}
        for rec in self:
            uuid = self.env['bus.exporter'].run_export(rec.id, force_domain)
            job_uuids[rec.id] = uuid
        return job_uuids[self.id] if len(self) == 1 else job_uuids

    def _create_cron(self, is_diff_cron, nextcall=False):
        """ protected : creates the cron"""
        self.ensure_one()

        if not nextcall:
            nextcall = fields.Datetime.to_string(datetime.now() + timedelta(minutes=1)) if is_diff_cron \
                else fields.Date.to_string(datetime.now() + timedelta(days=1)) + " 00:00:00"

        interval_number = 10 if is_diff_cron else 1
        interval_type = 'minutes' if is_diff_cron else 'days'

        method = 'sync_diff' if is_diff_cron else 'sync_all'
        cron_fk = 'bus_configuration_export_diff_id' if is_diff_cron else 'bus_configuration_export_id'

        return self.env['ir.cron'].create({
            cron_fk: self.id,
            'name': u"bus_%s %s" % (method, self.display_name),
            'user_id': 1,
            'priority': 100,
            'interval_type': interval_type,
            'interval_number': interval_number,
            'numbercall': -1,
            'doall': False,
            'model': 'bus.configuration.export',
            'function': method,
            'args': "(%s)" % repr([self.id]),
            'active': True,
            'nextcall': nextcall
        })

    @api.multi
    def create_cron_sync_diff(self):
        """ called from model form's button. button is displayed if cron created"""
        self._create_cron(True)

    @api.multi
    def create_cron_sync_all(self):
        self._create_cron(False)

    @api.multi
    def export_domain_keywords(self):
        """
        return a dict with
        keys: values to search and replace in domain
        values: replacement values
        """
        self.ensure_one()
        return {
            'date': datetime,
            'relativedelta': relativedelta.relativedelta,
            'self': self,
            'context': self.env.context,
            'date_to_str': fields.Date.to_string,
            'last_send_date': self.get_last_send_date(),
            'synchronized_record_ids': self.get_synchronized_record_ids(),
        }

    @api.multi
    def get_synchronized_record_ids(self):
        self.ensure_one()
        base = self.env.ref('bus_integration.backend').sender_id
        transfers = self.env['bus.receive.transfer'].search([('model', '=', self.model),
                                                             ('origin_base_id', '=', base.id)])
        return [transfer.local_id for transfer in transfers]

    @api.multi
    def get_last_send_date(self):
        """
        used by sync_diff to get the date of the last time the model have been synchronized
        :return:
        """
        self.ensure_one()
        last_send_date = datetime.strptime('1900', '%Y')  # default value
        if not self.cron_sync_diff and self.last_transfer_id:
            # Use last_transfer_date if no cron sync_diff
            last_send_date = fields.Datetime.from_string(self.last_transfer_id.write_date)
        elif self.cron_sync_diff:
            negative_interval = self.cron_sync_diff.interval_number * -1
            last_send_date = fields.Datetime.from_string(self.cron_sync_diff.nextcall) + \
                             _intervalTypes[self.cron_sync_diff.interval_type](negative_interval)
        if self.cron_sync_all:
            negative_interval_all = self.cron_sync_diff.interval_number * -1
            last_send_date_sync_all = fields.Datetime.from_string(self.cron_sync_all.nextcall) + \
                                      _intervalTypes[self.cron_sync_all.interval_type](negative_interval_all)
            if last_send_date_sync_all > last_send_date:
                last_send_date = last_send_date_sync_all
        return fields.Datetime.to_string(last_send_date)

    @api.multi
    def compute_dependency_level(self):
        for rec in self:
            rec.mapping_object_id.compute_dependency_level()
