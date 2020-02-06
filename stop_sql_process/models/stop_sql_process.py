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

from openerp import api, fields, models


class StopSqlProcess(models.TransientModel):
    _name = 'stop.sql.process'

    nb_lines = fields.Integer(u"Number of rows", compute='get_nb_lines')
    line_ids = fields.Many2many('stop.sql.process.line', string=u"Lines", readonly=True)

    @api.multi
    def kill_all(self):
        for rec in self:
            count = 0
            while count < 1000:
                self.env.cr.execute("""
                SELECT
                pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND pid <> pg_backend_pid();
                """)
                count += 1
            rec.write({'line_ids': [(6, 0, [])]})

    @api.multi
    def analyze(self):
        self.ensure_one()
        self.line_ids = False
        self.env.cr.execute("""
SELECT * FROM pg_stat_activity
WHERE state in ('active', 'idle in transaction')
AND query != 'COMMIT'
AND datname = current_database()
AND pid <> pg_backend_pid();
""")
        result = self.env.cr.dictfetchall()
        for line in result:
            self.line_ids |= self.env['stop.sql.process.line'].create({
                'pid': line['pid'],
                'query_start': line['query_start'],
                'query': line['query']
            })

    @api.multi
    @api.depends('line_ids')
    def get_nb_lines(self):
        for rec in self:
            rec.nb_lines = len(rec.line_ids)


class StopSqlProcessLine(models.TransientModel):
    _name = 'stop.sql.process.line'

    pid = fields.Integer(u"PID")
    query_start = fields.Datetime(u"Query start")
    query = fields.Char(u"Query")
