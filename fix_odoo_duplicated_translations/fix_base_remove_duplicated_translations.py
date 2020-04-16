# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from odoo import api, models, SUPERUSER_ID
from odoo.addons.base.models.ir_translation import IrTranslationImport

_logger = logging.getLogger(__name__)


class IrTranslationImportExtended(IrTranslationImport):
    """
    taken from: https://github.com/odoo/odoo/pull/32826
    Before this patch, importing a po file containing rows such as:

        #. modules: calendar, calendar_sms
        #: model:ir.model,name:calendar.model_calendar_event
        #: model:ir.model,name:calendar_sms.model_calendar_event
        msgid "Event"
        msgstr "Évènement"
    Was failing with "ON CONFLICT DO UPDATE command cannot affect row a second time"

    Both external ids calendar.model_calendar_event and calendar_sms.model_calendar_event target the same records
    (i.e. calendar_sms inherit from calendar.event model.

    After external id resolution, two entries in the temporary translation table are duplicated.
    In case of import with self._overwrite option, two update were done on the same row

    Apply the duplication removal on type model (to target ir.model and ir.model.fields) and selection
    (if the 2 modules modify the selections of the same column)
    """
    def finish(self):
        """ Transfer the data from the temp table to ir.translation """
        cr = self._cr

        # Step 0: insert rows in batch
        query = """ INSERT INTO %s (name, lang, res_id, src, type, imd_model,
                                    module, imd_name, value, state, comments)
                    VALUES """ % self._table
        for rows in cr.split_for_in_conditions(self._rows):
            cr.execute(query + ", ".join(["%s"] * len(rows)), rows)

        _logger.debug("ir.translation.cursor: We have %d entries to process", len(self._rows))

        # Step 1: resolve ir.model.data references to res_ids
        cr.execute(""" UPDATE %s AS ti
                          SET res_id = imd.res_id,
                              noupdate = imd.noupdate
                       FROM ir_model_data AS imd
                       WHERE ti.res_id IS NULL
                       AND ti.module IS NOT NULL AND ti.imd_name IS NOT NULL
                       AND ti.module = imd.module AND ti.imd_name = imd.name
                       AND ti.imd_model = imd.model; """ % self._table)

        if self._debug:
            cr.execute(""" SELECT module, imd_name, imd_model FROM %s
                           WHERE res_id IS NULL AND module IS NOT NULL """ % self._table)
            for row in cr.fetchall():
                _logger.info("ir.translation.cursor: missing res_id for %s.%s <%s> ", *row)

        # Records w/o res_id must _not_ be inserted into our db, because they are
        # referencing non-existent data.
        cr.execute("DELETE FROM %s WHERE res_id IS NULL AND module IS NOT NULL" % self._table)

        # detect the xml_translate fields, where the src must be the same
        env = api.Environment(cr, SUPERUSER_ID, {})
        src_relevant_fields = []
        for model in env:
            for field_name, field in env[model]._fields.items():
                if hasattr(field, 'translate') and callable(field.translate):
                    src_relevant_fields.append("%s,%s" % (model, field_name))

        count = 0
        # Step 2: insert new or upsert non-noupdate translations
        if self._overwrite:
            # After external id resolution, remove duplicated entries
            cr.execute("""DELETE FROM %s
                          WHERE id IN (
                            SELECT id FROM (
                                SELECT id, ROW_NUMBER() OVER (
                                    PARTITION BY type, lang, name, res_id
                                    ORDER BY id
                                ) as rnum
                                FROM %s
                                WHERE type in ('model', 'selection')
                            ) t
                            WHERE t.rnum > 1
                          )
                """ % (self._table, self._table))

            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'code'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, lang, md5(src)) WHERE type = 'code'
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                            (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value,
                            EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount
            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'model'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, lang, name, res_id) WHERE type = 'model'
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                            (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value,
                            EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount
            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type IN ('selection', 'constraint', 'sql_constraint')
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, lang, name, md5(src)) WHERE type IN
                           ('selection', 'constraint', 'sql_constraint')
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                            (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value,
                            EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount
            cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                           SELECT name, lang, res_id, src, type, value, module, state, comments
                           FROM %s
                           WHERE type = 'model_terms'
                           AND noupdate IS NOT TRUE
                           ON CONFLICT (type, name, lang, res_id, md5(src))
                            DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                            (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type, EXCLUDED.value,
                            EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                            WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != '';
                       """ % (self._model_table, self._table))
            count += cr.rowcount
        cr.execute(""" INSERT INTO %s(name, lang, res_id, src, type, value, module, state, comments)
                       SELECT name, lang, res_id, src, type, value, module, state, comments
                       FROM %s
                       WHERE %s
                       ON CONFLICT DO NOTHING;
                   """ % (self._model_table, self._table, 'noupdate IS TRUE' if self._overwrite else 'TRUE'))
        count += cr.rowcount

        if self._debug:
            cr.execute("SELECT COUNT(*) FROM ONLY %s" % self._model_table)
            total = cr.fetchone()[0]
            _logger.debug("ir.translation.cursor: %d entries now in ir.translation, %d common entries with tmp",
                          total, count)

        # Step 3: cleanup
        cr.execute("DROP TABLE %s" % self._table)
        self._rows.clear()
        return True


class IrTranslation(models.Model):
    _inherit = "ir.translation"

    @api.model
    def _get_import_cursor(self):
        """ Return a cursor-like object for fast inserting translations """
        return IrTranslationImportExtended(self)
