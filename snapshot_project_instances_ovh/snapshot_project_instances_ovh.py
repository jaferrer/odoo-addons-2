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

import logging
import os
import subprocess
from datetime import datetime as dt

from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

import openerp.tools as tools
from openerp import models, fields, api, exceptions, _
from openerp.tools.config import config

logger = logging.getLogger('snapshot_project_instances_ovh')


@job(default_channel='root')
def snapshot(session, model_name, request_id, area, app_key, app_secret, consumer_key, min_hour_snapshot,
             max_hour_snapshot, script_location):
    hour = dt.now().hour
    if hour > max_hour_snapshot or hour < min_hour_snapshot:
        return _("Snapshot request aborted: forbidden to snapshot at %s h. "
                 "Snapshot are allowed only between %s h and %s h (GMT)" % (hour, min_hour_snapshot, max_hour_snapshot))
    rec = session.pool[model_name].browse(session.cr, session.uid, request_id, session.context)
    project_name = rec.project_id.name
    instance_name = rec.instance_id.name
    nb_max_snapshots = rec.nb_max_snapshots
    nb_days_between_snapshots = rec.nb_days_between_snapshots
    # Let's launch OCH snapshot script
    result = subprocess.call(['python', script_location, area, app_key, app_secret, consumer_key, project_name,
                              instance_name, str(nb_max_snapshots), str(nb_days_between_snapshots)])
    return _("Script executed, returned %s") % result


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

    @api.model
    def load_from_file(self, path, script_name):
        try:
            ad = os.path.abspath(os.path.join(tools.ustr(config['root_path']), u'addons'))
            mod_path_list = map(lambda m: os.path.abspath(tools.ustr(m.strip())), config['addons_path'].split(','))
            mod_path_list.append(ad)
            mod_path_list = list(set(mod_path_list))
            for mod_path in mod_path_list:
                if os.path.lexists(mod_path + os.path.sep + path.split(os.path.sep)[0]):
                    filepath = mod_path + os.path.sep + path + os.path.sep + script_name
                    filepath = os.path.normpath(filepath)
                    if filepath:
                        return filepath
        except SyntaxError, e:
            raise exceptions.except_orm(_('Syntax Error !'), e)
        except Exception, e:
            logger.error(_('Error loading script: %s') + (filepath and ' "%s"' % filepath or ''), e)
            return None

    @api.multi
    def ask_for_snapshots(self):
        script_location = self.load_from_file('snapshot_project_instances_ovh', 'ovh_snapshot_script.py')
        area = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.area')
        app_key = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.app_key')
        app_secret = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.app_secret')
        consumer_key = self.env['ir.config_parameter'].get_param('snapshot_project_instances_ovh.consumer_key')
        min_hour_snapshot = int(self.env['ir.config_parameter']. \
                                get_param('snapshot_project_instances_ovh.min_hour_snapshot') or 0)
        max_hour_snapshot = int(self.env['ir.config_parameter']. \
                                get_param('snapshot_project_instances_ovh.max_hour_snapshot') or 0)
        if area and app_key and app_secret and consumer_key:
            for rec in self:
                session = ConnectorSession(self.env.cr, self.env.user.id, self.env.context)
                description = _("Creation of snapshot for project %s on instance %s.") % \
                              (rec.project_id.name, rec.instance_id.name)
                snapshot.delay(session, 'snapshot.request.line', rec.id, area, app_key, app_secret, consumer_key,
                               min_hour_snapshot, max_hour_snapshot, description=description, priority=1,
                               script_location=script_location)
        else:
            raise exceptions.except_orm(_("Error!"), _("Please fill entirely the OVH hosting configuration."))
