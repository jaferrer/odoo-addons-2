# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists


class ProjectTaskCharge(models.Model):
    _name = 'project.task.charge'
    _auto = False
    _order = 'date, user_id'

    id = fields.Integer(u"ID")
    date = fields.Date(u"Date")
    num_day_week = fields.Integer(u"Day of the week")
    project_id = fields.Many2one('project.project', u"Project")
    task_id = fields.Many2one('project.task', u"Task")
    user_id = fields.Many2one('res.users', u"User")
    stage_id = fields.Many2one('project.task.type', u"Stage")
    duration_per_day = fields.Float(u"Duration of the task per day")
    duration = fields.Integer(u"Spacing the task in days")
    planned_hours = fields.Float(u"Planned hours")
    total_hours_spent = fields.Float(u"Total hours spent")
    remaining_hours = fields.Float(u"Remaining hours")
    date_start = fields.Datetime(u"Start date")
    date_end = fields.Datetime(u"End date")

    api.multi

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, u"%s %s" % (rec.user_id.name or u"Unassigned", rec.task_id.name or u"No task")))
        return result

    @api.model_cr
    def init(self):
        drop_view_if_exists(self.env.cr, 'project_task_charge')
        self.env.cr.execute("""
 CREATE OR REPLACE VIEW project_task_charge AS (
    WITH max_task_date AS (
    SELECT max(date_end) AS max_date
    FROM project_task
),
     min_task_date AS (
         SELECT min(date_start) AS min_date
         FROM project_task
     ),
     days AS (
         SELECT generate_days.date,
                EXTRACT(DOW FROM generate_days.date::TIMESTAMP) AS num_day_week
         FROM generate_series((SELECT min_date
                               FROM min_task_date),
                              (SELECT max_date
                               FROM max_task_date), '1 days') AS generate_days(date)
     ),
     task_data AS (
         SELECT pt.project_id,
                pt.user_id,
                pt.id AS task_id,
                pt.stage_id,
                duration_per_day,
                duration,
                pt.date_start,
                pt.date_end,
                planned_hours,
                total_hours_spent,
                remaining_hours
         FROM project_task pt
     )
SELECT (to_char(days.date, 'yyyymmdd') || lpad(COALESCE(td.user_id::TEXT, '')::TEXT, 4, '0') ||
       lpad(COALESCE(td.task_id::TEXT, '')::TEXT, 5, '0')) AS id,
             days.date::DATE AS date,
             days.num_day_week AS num_day_week,
             td.project_id AS project_id,
             td.user_id AS user_id,
             td.task_id AS task_id,
             td.stage_id AS stage_id,
             td.duration_per_day AS duration_per_day,
             td.duration AS duration,
             td.planned_hours AS planned_hours,
             td.total_hours_spent AS total_hours_spent,
             td.remaining_hours AS remaining_hours,
             td.date_start AS date_start,
             td.date_end AS date_end
    FROM days
             LEFT JOIN task_data td ON days.date > td.date_start AND days.date < td.date_end
    WHERE days.num_day_week > 0
      AND days.num_day_week < 6
)
        """)
