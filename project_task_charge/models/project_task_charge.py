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
    department_id = fields.Many2one('hr.department', u"Department")
    sale_order_line_amount = fields.Float(string=u"Sale order line amount")
    sale_order_line_amount_per_day = fields.Float(string=u"Sale order line amount per day")
    stage_id = fields.Many2one('project.task.type', u"Stage")
    duration_per_day = fields.Float(u"Duration of the task")
    percent_duration = fields.Float(u"Duration in percent", group_operator='avg')
    percent_advancement = fields.Float(u"Percent of the advancement", group_operator='avg')
    duration = fields.Integer(u"Spacing the task in days")
    planned_hours = fields.Float(u"Planned hours")
    total_hours_spent = fields.Float(u"Total hours spent")
    remaining_hours = fields.Float(u"Remaining hours")
    spent_by_day = fields.Float(u"Spent by day")
    date_start = fields.Datetime(u"Start date")
    date_end = fields.Datetime(u"End date")

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, u"%s %s" % (rec.user_id.name or u"Unassigned", rec.task_id.name or u"No task")))
        return result

    @api.model
    def get_select_task(self):
        return """
        pt.project_id,
        pt.user_id,
        pt.id                           AS task_id,
        pt.stage_id,
        hrd.id                          AS department_id,
        sol.price_subtotal,
        date_deadline,
        planned_hours,
        total_hours_spent,
        remaining_hours
        """

    @api.model
    def get_join_task(self):
        return """
        LEFT JOIN sale_order_line sol ON pt.sale_line_id = sol.id
        LEFT JOIN hr_employee hre ON hre.resource_id = pt.user_id
        LEFT JOIN hr_department hrd ON hre.department_id = hrd.id
        LEFT JOIN days ON days.date > pt.date_start AND days.date < pt.date_end AND days.date < pt.date_end
        AND days.num_day_week > 0 AND days.num_day_week < 6
        """

    @api.model
    def get_groupby_task(self):
        return """
        pt.id,
        pt.project_id,
        pt.user_id,
        task_id,
        pt.stage_id,
        hrd.id,
        sol.price_subtotal,
        pt.date_start,
        pt.date_end,
        pt.date_deadline,
        planned_hours,
        total_hours_spent,
        remaining_hours
        """

    @api.model
    def get_select_data(self):
        return """
        days.date::DATE                                                      AS date,
        days.num_day_week                                                    AS num_day_week,
        td.project_id                                                        AS project_id,
        td.user_id                                                           AS user_id,
        td.task_id                                                           AS task_id,
        td.department_id                                                     AS department_id,
        td.stage_id                                                          AS stage_id,
        td.date_start                                                        AS date_start,
        td.date_end                                                          AS date_end,
        td.price_subtotal                                                    AS sale_order_line_amount,
         CASE count(nb_days.date)
           WHEN 0 THEN 1
           ELSE count(nb_days.date)
        END                                                 AS duration,
        (td.planned_hours / CASE count(nb_days.date)
           WHEN 0 THEN 1
           ELSE count(nb_days.date)
        END)                             AS duration_per_day,
        (td.price_subtotal / td.planned_hours *  (td.planned_hours /
        CASE count(nb_days.date)
           WHEN 0 THEN 1
           ELSE count(nb_days.date)
           END))                                                             AS sale_order_line_amount_per_day,
        td.planned_hours                                                     AS planned_hours,
        td.total_hours_spent                                                 AS total_hours_spent,
        td.remaining_hours                                                   AS remaining_hours,
        hs.spent_by_day                                                      AS spent_by_day,
        coalesce(((td.planned_hours /
        CASE count(nb_days.date)
           WHEN 0 THEN 1
           ELSE count(nb_days.date)
        END) / 7 * 100), 0)    AS percent_duration,
        coalesce((hs.spent_by_day / (td.planned_hours /
        CASE count(nb_days.date)
           WHEN 0 THEN 1
           ELSE count(nb_days.date)
        END
        ) * 100), 0)                                                         AS percent_advancement
        """

    @api.model
    def get_date_start(self):
        return """
        CASE
            WHEN pt.date_start IS NULL
                THEN (SELECT NOW())
            WHEN pt.date_start <= (SELECT NOW())
                THEN (SELECT NOW())
            ELSE pt.date_start
        END
        """

    @api.model
    def get_date_end(self):
        return """
           CASE
                WHEN pt.date_end IS NULL AND pt.date_deadline IS NOT NULL
                    THEN pt.date_deadline
                WHEN pt.date_end IS NULL AND pt.date_deadline IS NULL
                    THEN CASE
                        WHEN pt.planned_hours IS NOT NULL
                            THEN (pt.date_start + interval '1 hours' * pt.planned_hours)
                        ELSE (pt.date_start + interval '1 hours')
                    END
                ELSE pt.date_end
            END
            """

    @api.model
    def get_join_data(self):
        return ""

    @api.model
    def get_groupby_data(self):
        return """
           days.date,
           days.num_day_week,
           td.project_id,
           td.user_id,
           td.task_id,
           td.department_id,
           td.stage_id,
           td.date_start,
           td.date_end,
           td.price_subtotal,
           td.planned_hours,
           td.total_hours_spent,
           td.remaining_hours,
           hs.spent_by_day
           """

    @api.model_cr
    def init(self):
        drop_view_if_exists(self.env.cr, 'project_task_charge')
        sql = """
 CREATE OR REPLACE VIEW project_task_charge AS (
    WITH max_task_date AS (
        SELECT NOW() + interval '1 month' *
        CASE (select coalesce (value::INT, 0) from ir_config_parameter where key = 'project_task_charge.calc_max_date')
       WHEN 0 THEN 1
       ELSE (select coalesce (value::INT, 0) from ir_config_parameter where key = 'project_task_charge.calc_max_date')
     END as max_date
    ),
     min_task_date AS (
     SELECT NOW() - interval '1 month' *
     CASE (select coalesce (value::INT, 0) from ir_config_parameter where key = 'project_task_charge.calc_min_date')
       WHEN 0 THEN 1
       ELSE (select coalesce (value::INT, 0) from ir_config_parameter where key = 'project_task_charge.calc_min_date')
     END as min_date
     ),
     days AS (
         SELECT generate_days.date,
                EXTRACT(DOW FROM generate_days.date::TIMESTAMP) AS num_day_week
         FROM generate_series((SELECT min_date
                               FROM min_task_date),
                              (SELECT max_date
                               FROM max_task_date), '1 days') AS generate_days(date)
     ),
     hours_spent AS (
         SELECT SUM(unit_amount) as spent_by_day,
                user_id,
                task_id,
                date
         FROM account_analytic_line
         GROUP BY user_id, task_id, date
     ),
     task_data AS (
         SELECT %s, %s as date_start, %s as date_end
         FROM project_task pt
         %s
         GROUP BY %s
     )
SELECT (to_char(days.date, 'yyyymmdd') || lpad(COALESCE(td.user_id::TEXT, '')::TEXT, 4, '0') ||
        lpad(COALESCE(td.task_id::TEXT, '')::TEXT, 5, '0'))                 AS id,
        %s
FROM days
    LEFT JOIN task_data td ON days.date >= td.date_start AND days.date <= td.date_end
    LEFT JOIN hours_spent hs ON days.date::DATE = hs.date AND td.user_id = hs.user_id and hs.task_id = td.task_id
    LEFT JOIN days nb_days ON nb_days.date > date_start and nb_days.date < date_end and nb_days.num_day_week > 0
    AND nb_days.num_day_week < 6
    %s
WHERE days.num_day_week > 0
  AND days.num_day_week < 6
  GROUP BY
    %s
  )""" % (self.get_select_task(), self.get_date_start(), self.get_date_end(), self.get_join_task(),
          self.get_groupby_task(), self.get_select_data(), self.get_join_data(), self.get_groupby_data())
        return self.env.cr.execute(sql)
