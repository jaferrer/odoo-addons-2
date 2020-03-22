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

from iso8601 import iso8601

from odoo import models, fields, api, _ as _t


_logger = logging.getLogger(__name__)


def _field_ident(env, field):
    return field


def _field_iso8601_date(env, field):
    return iso8601.parse_date(field.replace(' ', '+'))


def _field_std_date(env, field):
    return fields.Datetime.from_string(field)


def _field_comment(env, field):
    return [(0, 0, env['avis.verifies.comment'].vals_from_json(comment)) for comment in field]


def _field_bool(env, field):
    return field == u"oui"


def _field_origin(env, field):
    origins = {
        '2': 'vendor',
        '3': 'client',
    }
    return origins.get(field, False)


class AvisVerifiesJson(models.AbstractModel):
    _name = 'avis.verifies.json'

    # [(field_name_in_json, conversion_function, field_name_in_odoo), ...]
    _FIELDS_FROM_JSON = ()

    @api.model
    def vals_from_json(self, dct):
        vals = {}
        to_handle = dct.keys()
        for (json_field, fun, odoo_field) in self._FIELDS_FROM_JSON:
            if json_field in dct:
                vals[odoo_field or json_field] = fun(self.env, dct.get(json_field))
                to_handle.remove(json_field)

        if to_handle:
            _logger.info(_t(u"In avis-verifies' import: fields %s from the api json not handled by the model %s"),
                         u", ".join(to_handle), self._name)

        return vals
