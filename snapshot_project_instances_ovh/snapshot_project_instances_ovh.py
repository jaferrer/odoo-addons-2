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
from datetime import timedelta, datetime as dt
from ovh import Client, APIError
from openerp.addons.connector.session import ConnectorSession, ConnectorSessionHandler
from openerp.addons.connector.queue.job import job


@job(default_channel='root')
def snapshot(session, model_name, request_id, area, app_key, app_secret, consumer_key, min_hour_snapshot, max_hour_snapshot):
    hour = dt.now().hour
    if hour < min_hour_snapshot or hour > max_hour_snapshot:
        return _("Snapshot request aborted: forbidden to snapshot at %s h. "
                 "Snapshot are allowed only between %s h and %s h (GMT)" % (hour, min_hour_snapshot, max_hour_snapshot))
    rec = session.pool[model_name].browse(session.cr, session.uid, request_id, session.context)
    handler = ConnectorSessionHandler(session.cr.dbname, session.uid, session.context)
    with handler.session() as s:
        result = _("Project %s not found.") % rec.project_id.name
        client = Client(endpoint=area, application_key=app_key,
                        application_secret=app_secret, consumer_key=consumer_key)
        project_ids = client.get('/cloud/project')
        if rec.project_id.name in project_ids:
            instances = rec.project_id.name and client.get('/cloud/project/%s/instance' % rec.project_id.name) or []
            instance = [instance for instance in instances if instance.get('name') == rec.instance_id.name]
            instance = instance and instances[0].get('id') or False
            result = _("Instance %s not found.") % rec.instance_id.name
            if instance:
                result = _("Nothing to do.")
                snapshots = rec.project_id.name and client.get('/cloud/project/%s/snapshot' % rec.project_id.name) or []
                for s in snapshots:
                    s['formated_date'] = s.get('creationDate') and \
                                         fields.Datetime.from_string(
                                             s['creationDate'][:10] + ' ' + s['creationDate'][11:19]) or False
                max_snap_date = snapshots and max([snap['formated_date'] for snap in snapshots]) or False
                max_snap_date = max_snap_date and fields.Datetime.to_string(max_snap_date)[:10] or False
                if max_snap_date and max_snap_date > rec.next_snapshot_date:
                    rec.last_snapshot_date = max_snap_date
                    rec.update_next_snapshot_date()
                if rec.next_snapshot_date <= fields.Date.today():
                    client.post('/cloud/project/%s/instance/%s/snapshot' % (rec.project_id.name, instance),
                                snapshotName=' - '.join([rec.project_id.name, rec.instance_id.name,
                                                         fields.Datetime.now()]))
                    return _("Snapshot request created for project %s on instance %s.") % \
                           (rec.project_id.name, rec.instance_id.name)
                if rec.nb_max_snapshots and len(snapshots) > rec.nb_max_snapshots - 1:
                    snapshots_to_delete = sorted(snapshots,key=lambda dictionnary: \
                        dictionnary.get('formated_date'))[:rec.nb_max_snapshots]
                    to_delete_ids = [dictionnary.get('id') for dictionnary in snapshots_to_delete if \
                                     dictionnary.get('id')]
                    if to_delete_ids:
                        for to_delete_id in to_delete_ids:
                            try:
                                client.delete('/cloud/project/%s/snapshot/%s' % (rec.project_id.name, to_delete_id,))
                            except APIError:
                                pass
                        result = _("Deletion request created for snapshots %s" %
                                    ', '.join([snap_id for snap_id in to_delete_ids]))
    return result


class OvhProject(models.Model):
    _name = 'ovh.project'

    name = fields.Char(string="OVH ID")


class OvhInstance(models.Model):
    _name = 'ovh.instance'

    name = fields.Char(string="Name")


class SnapshotRequestLine(models.Model):
    _name = 'snapshot.request.line'

    project_id = fields.Many2one('ovh.project', string="Project name", required=True)
    instance_id = fields.Many2one('ovh.instance', string="Instance ID", required=True)
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
        min_hour_snapshot = int(self.env['ir.config_parameter']. \
            get_param('snapshot_project_instances_ovh.min_hour_snapshot') or 0)
        max_hour_snapshot = int(self.env['ir.config_parameter']. \
            get_param('snapshot_project_instances_ovh.max_hour_snapshot') or 0)
        self.update_next_snapshot_date()
        if area and app_key and app_secret and consumer_key:
            for rec in self:
                session = ConnectorSession(self.env.cr, self.env.user.id, self.env.context)
                description = _("Creation of snapshot for project %s on instance %s.") % \
                              (rec.project_id.name, rec.instance_id.name)
                snapshot.delay(session, 'snapshot.request.line', rec.id, area, app_key, app_secret, consumer_key,
                               min_hour_snapshot, max_hour_snapshot, description=description, priority=1)
        else:
            raise exceptions.except_orm(_("Error!"), _("Please fill entirely the OVH hosting configuration."))
