# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, api


class SQLfunctions(models.AbstractModel):
    _name = 'group.operator'
    _auto = False

    @api.model_cr
    def init(self):
        self._cr.execute("""
                CREATE OR REPLACE FUNCTION public.first_agg ( anyelement, anyelement )
                RETURNS anyelement LANGUAGE sql IMMUTABLE STRICT AS $$
                    SELECT $1;
                $$;

                DROP AGGREGATE IF EXISTS public.first(anyelement) CASCADE;
                CREATE AGGREGATE public.first (
                    sfunc    = public.first_agg,
                    basetype = anyelement,
                    stype    = anyelement
                );

                CREATE OR REPLACE FUNCTION public.last_agg ( anyelement, anyelement )
                RETURNS anyelement LANGUAGE sql IMMUTABLE STRICT AS $$
                    SELECT $2;
                $$;

                DROP AGGREGATE IF EXISTS public.last(anyelement) CASCADE;
                CREATE AGGREGATE public.last (
                    sfunc    = public.last_agg,
                    basetype = anyelement,
                    stype    = anyelement
                );
                """)
        self._cr.execute("""
        CREATE OR REPLACE FUNCTION public.median_agg(anyarray)
        RETURNS FLOAT8 LANGUAGE SQL IMMUTABLE STRICT AS $$
            SELECT percentile_cont(0.5)
            WITHIN GROUP (ORDER BY result.val)
            from (select val from unnest($1) val) result
        $$;

        DROP AGGREGATE IF EXISTS public.median(anyelement) CASCADE;
        CREATE AGGREGATE public.median(ANYELEMENT) (
            SFUNC=array_append,
            STYPE=anyarray,
            FINALFUNC=median_agg,
            INITCOND='{}'
        );
        """)
        self._cr.execute("""
                -- Positive average
                CREATE OR REPLACE FUNCTION public.pos_avg_agg(anyarray)
                RETURNS FLOAT8 LANGUAGE SQL IMMUTABLE STRICT AS $$
                    SELECT avg(val) filter (where val >= 0)
                    FROM unnest($1) val
                $$;

                DROP AGGREGATE IF EXISTS public.pos_avg(anyelement) CASCADE;
                CREATE AGGREGATE public.pos_avg(anyelement) (
                    SFUNC=array_append,
                    STYPE=anyarray,
                    FINALFUNC=pos_avg_agg,
                    INITCOND='{}'
                );
                """)
