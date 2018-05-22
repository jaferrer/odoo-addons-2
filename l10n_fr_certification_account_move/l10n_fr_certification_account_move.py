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

import datetime

import babel.dates
import dateutil
import pytz

from openerp import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    validation_date = fields.Datetime(string=u"Date de validation", readonly=True)
    validation_uid = fields.Many2one('res.users', string=u"Validé par", readonly=True)
    
    @api.multi
    def write(self, vals):
        if vals.get('state') == 'posted':
            vals['validation_date'] = fields.Datetime.now()
            vals['validation_uid'] = self.env.uid
        return super(AccountMove, self).write(vals)

    def _read_group_format_result(self, data, annotated_groupbys, groupby, groupby_dict, domain, context):
        """
            Helper method to format the data contained in the dictionary data by
            adding the domain corresponding to its values, the groupbys in the
            context and by properly formatting the date/datetime values.
        """
        domain_group = [dom for gb in annotated_groupbys for dom in self._read_group_get_domain(gb, data[gb['groupby']])]
        for k,v in data.iteritems():
            gb = groupby_dict.get(k)
            if gb and gb['type'] in ('date', 'datetime') and v:
                data[k] = babel.dates.format_datetime(v, format=gb['display_format'], locale=context.get('lang', 'en_US'))

        data['__domain'] = domain_group + domain
        if len(groupby) - len(annotated_groupbys) >= 1:
            data['__context'] = { 'group_by': groupby[len(annotated_groupbys):]}
        del data['id']
        return data

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """This function is overwritten to group by hour and minute"""
        split = gb.split(':')
        field_type = self._fields[split[0]].type
        gb_function = split[1] if len(split) == 2 else None
        temporal = field_type in ('date', 'datetime')
        tz_convert = field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones
        qualified_field = self._inherits_join_calc(self._table, split[0], query)
        if temporal:
            display_formats = {
                'minute': "dd MMM yyyy hh':'mm",  # yyyy = normal year
                'hour': "dd MMM yyyy hh'h'",  # yyyy = normal year
                'day': 'dd MMM yyyy',  # yyyy = normal year
                'week': "'W'w YYYY",  # w YYYY = ISO week-year
                'month': 'MMMM yyyy',
                'quarter': 'QQQ yyyy',
                'year': 'yyyy',
            }
            time_intervals = {
                'minute': dateutil.relativedelta.relativedelta(minutes=1),
                'hour': dateutil.relativedelta.relativedelta(hours=1),
                'day': dateutil.relativedelta.relativedelta(days=1),
                'week': datetime.timedelta(days=7),
                'month': dateutil.relativedelta.relativedelta(months=1),
                'quarter': dateutil.relativedelta.relativedelta(months=3),
                'year': dateutil.relativedelta.relativedelta(years=1)
            }
            if tz_convert:
                qualified_field = "timezone('%s', timezone('UTC',%s))" % (
                self._context.get('tz', 'UTC'), qualified_field)
            qualified_field = "date_trunc('%s', %s)" % (gb_function or 'month', qualified_field)
        if field_type == 'boolean':
            qualified_field = "coalesce(%s,false)" % qualified_field
        return {
            'field': split[0],
            'groupby': gb,
            'type': field_type,
            'display_format': display_formats[gb_function or 'month'] if temporal else None,
            'interval': time_intervals[gb_function or 'month'] if temporal else None,
            'tz_convert': tz_convert,
            'qualified_field': qualified_field
        }
