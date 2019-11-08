# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp.tests import common

_logger = logging.getLogger(__name__)

TABLES_REQUIRED_FK_ON_INCOMING_FK = ['procurement_order', 'stock_move']


class TestStockPerformanceImproved(common.TransactionCase):
    at_install = False
    post_install = True

    def test_10_indexes_procurements(self):
        missing_indexes = []
        for table_to_check in TABLES_REQUIRED_FK_ON_INCOMING_FK:
            self.env.cr.execute("""SELECT tc.table_schema,
           tc.table_name,
           kcu.column_name
    FROM information_schema.table_constraints AS tc
           JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
           JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND ccu.table_name = %s""", (table_to_check,))
            for schema, table_name, column_name in self.env.cr.fetchall():
                _logger.info(u"Checking index for column %s of table %s in schema %s, pointing to table %s",
                             column_name, table_name, schema, table_to_check)
                indexname = '_'.join([table_name, column_name, 'index'])
                self.env.cr.execute("""SELECT tablename,
       indexname
FROM pg_indexes
WHERE schemaname = %s AND
      tablename = %s AND
      indexname = %s""", (schema, table_name, indexname))
                if not self.env.cr.fetchall():
                    missing_indexes += [indexname]
        self.assertFalse(missing_indexes, u"Required index(es) %s missing" % (u", ".join(missing_indexes)))
