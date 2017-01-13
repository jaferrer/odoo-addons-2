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

import os
import sys
from datetime import timedelta, datetime as dt

from ovh import Client, APIError

if __name__ == "__main__":
    area = sys.argv[1]
    app_key = sys.argv[2]
    app_secret = sys.argv[3]
    consumer_key = sys.argv[4]
    project_name = sys.argv[5]
    instance_name = sys.argv[6]
    nb_max_snapshots = int(sys.argv[7])
    nb_days_between_snapshots = int(sys.argv[8])
    client = Client(endpoint=area, application_key=app_key, application_secret=app_secret, consumer_key=consumer_key)
    project_ids = client.get('/cloud/project')
    if project_name in project_ids:
        instances = project_name and client.get('/cloud/project/%s/instance' % project_name) or []
        instance = [instance for instance in instances if instance.get('name') == instance_name]
        instance = instance and instances[0].get('id') or False
        if instance:
            snapshots = project_name and client.get('/cloud/project/%s/snapshot' % project_name) or []
            for snapshot in snapshots:
                year = int(snapshot['creationDate'][:4])
                month = int(snapshot['creationDate'][5:7])
                day = int(snapshot['creationDate'][8:10])
                hour = int(snapshot['creationDate'][11:13])
                minute = int(snapshot['creationDate'][14:16])
                second = int(snapshot['creationDate'][17:19])
                snapshot['formated_date'] = snapshot.get('creationDate') and \
                                     dt(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
            last_snapshot_date = snapshots and max([snapshot['formated_date'] for snapshot in snapshots]) or False
            next_snapshot_date = last_snapshot_date and nb_days_between_snapshots and \
                                 last_snapshot_date + timedelta(days=nb_days_between_snapshots)
            if not next_snapshot_date or next_snapshot_date <= dt.today():
                date_snapshot = '%s-%s-%s %s:%s:%s' % (str(dt.now().year), str(dt.now().month), str(dt.now().day),
                                                       str(dt.now().hour), str(dt.now().minute), str(dt.now().second))
                client.post('/cloud/project/%s/instance/%s/snapshot' % (project_name, instance),
                            snapshotName=' - '.join([project_name, instance_name, date_snapshot]))
            if nb_max_snapshots and len(snapshots) > nb_max_snapshots - 1:
                snapshots_to_delete = sorted(snapshots, key=lambda dictionnary: \
                    dictionnary.get('formated_date'))[:nb_max_snapshots]
                to_delete_ids = [dictionnary.get('id') for dictionnary in snapshots_to_delete if dictionnary.get('id')]
                if to_delete_ids:
                    for to_delete_id in to_delete_ids:
                        try:
                            client.delete('/cloud/project/%s/snapshot/%s' % (project_name, to_delete_id,))
                        except APIError:
                            pass
    os._exit(0)
