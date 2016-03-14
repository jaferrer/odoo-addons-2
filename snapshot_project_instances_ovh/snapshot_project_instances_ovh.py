# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api, exceptions, _
from datetime import timedelta
import time
from ovh import Client, APIError
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler
from openerp.addons.connector.queue.job import job


@job(default_channel='root')
def snapshot(session, model_name, request_id, area, app_key, app_secret, consumer_key):
    rec = session.pool[model_name].browse(session.cr, session.uid, request_id, session.context)
    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as s:
        result = _("Project %s not found.") % rec.project_id.name
        client = Client(endpoint=area, application_key=app_key,
                        application_secret=app_secret, consumer_key=consumer_key)
        project_ids = client.get('/cloud/project')
        project_id = project_ids and project_ids[0] or []
        for project in project_ids:
            properties = client.get('/cloud/project/%s' % project)
            if properties.get('description') == rec.project_id.name:
                project_id = project
                break
        if project_id:
            instances = project_id and client.get('/cloud/project/%s/instance' % project_id) or []
            instance = [instance for instance in instances if instance.get('name') == rec.instance_id.name]
            instance = instance and instances[0].get('id') or False
            result = _("Instance %s not found.") % rec.instance_id.name
            if instance:
                snapshots = project_id and client.get('/cloud/project/%s/snapshot' % project_id) or []
                for s in snapshots:
                    s['formated_date'] = s.get('creationDate') and \
                                         fields.Datetime.from_string(
                                             s['creationDate'][:10] + ' ' + s['creationDate'][11:19]) or False
                if rec.nb_max_snapshots and len(snapshots) > rec.nb_max_snapshots - 1:
                    snapshots_to_delete = sorted(snapshots,key=lambda dictionnary: \
                        dictionnary.get('formated_date'))[:rec.nb_max_snapshots]
                    to_delete_ids = [dictionnary.get('id') for dictionnary in snapshots_to_delete if \
                                     dictionnary.get('id')]
                    if to_delete_ids:
                        for to_delete_id in to_delete_ids:
                            try:
                                client.delete('/cloud/project/%s/snapshot/%s' % (project_id, to_delete_id,))
                            except APIError:
                                pass
                        time.sleep(120)
                        snapshots = project_id and client.get('/cloud/project/%s/snapshot' % project_id) or []
                        not_deleted_id = []
                        for to_delete_id in to_delete_ids:
                            if [snapshot.get('id') for snapshot in snapshots] and \
                                    to_delete_id in [snapshot.get('id') for snapshot in snapshots]:
                                not_deleted_id += [to_delete_id]
                        if not_deleted_id:
                            raise exceptions.except_orm(_("Error!"),
                                                        _("Snapshot deletion could not be checked for ids %s.") %
                                                        ', '.join(not_deleted_id))
                client.post('/cloud/project/%s/instance/%s/snapshot' % (project_id, instance),
                            snapshotName=' - '.join([rec.project_id.name, rec.instance_id.name, fields.Datetime.now()]))
                rec.last_snapshot_date = fields.Date.today()
                rec.update_next_snapshot_date()
                result = _("Snapshot created for project %s on instance %s.") % \
                         (rec.project_id.name, rec.instance_id.name)
    return result


class OvhProject(models.Model):
    _name = 'ovh.project'

    name = fields.Char(string="Name")


class OvhInstance(models.Model):
    _name = 'ovh.instance'

    name = fields.Char(string="Name")


class SnapshotRequestLine(models.Model):
    _name = 'snapshot.request.line'

    project_id = fields.Many2one('ovh.project', string="Project", required=True)
    instance_id = fields.Many2one('ovh.instance', string="Instance", required=True)
    nb_days_between_snapshots = fields.Integer(string="Number of days between two snapshots")
    nb_max_snapshots = fields.Integer(string="Maximal number of snapshots to keep")
    last_snapshot_date = fields.Date(string="Last snapshot date", readonly=True)
    next_snapshot_date = fields.Date(string="Next snapshot date", readonly=True, default=fields.Date.today())

    @api.multi
    def update_next_snapshot_date(self):
        for rec in self:
            rec.next_snapshot_date = rec.last_snapshot_date and \
                                     rec.nb_days_between_snapshots and \
                                     fields.Date.to_string(fields.Date.from_string(rec.last_snapshot_date) +
                                                           timedelta(days=rec.nb_days_between_snapshots)) or \
                                     fields.Date.today()

    @api.multi
    def ask_for_snapshots(self):
        area = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.area')
        app_key = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.app_key')
        app_secret = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.app_secret')
        consumer_key = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.consumer_key')
        self.update_next_snapshot_date()
        if area and app_key and app_secret and consumer_key:
            requests = self.filtered(lambda req: req.next_snapshot_date >= fields.Date.today())
            if requests:
                for rec in requests:
                    session = ConnectorSession(self.env.cr, self.env.user.id, self.env.context)
                    description = _("Creation of snapshot for project %s on instance %s.") % \
                                  (rec.project_id.name, rec.instance_id.name)
                    snapshot.delay(session, 'snapshot.request.line', rec.id, area, app_key, app_secret, consumer_key,
                                   description=description, priority=1)
            else:
                raise exceptions.except_orm(_("Error!"), _("No snapshot required."))
        else:
            raise exceptions.except_orm(_("Error!"), _("Please fill entirely the OVH hosting configuration."))
