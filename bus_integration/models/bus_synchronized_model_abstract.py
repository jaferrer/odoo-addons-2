# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#    along with this
#


import logging

from openerp import fields, models, api, exceptions, _

_logger = logging.getLogger(__name__)


class BusSynchronizedModelAbstract(models.AbstractModel):
    _name = 'bus.synchronized.model'

    # store last write date on fields concerned by the bus (exported fields)
    write_date_bus = fields.Datetime(u"bus write date", default=lambda _: fields.Datetime.now(), required=True)

    @api.model
    def _vals_contains_a_mapped_exported_field(self, vals):
        mapping = self.env['bus.object.mapping'].get_mapping(self._name)
        mapping_field_names = mapping.field_ids\
            .filtered(lambda x: x.export_field)\
            .mapped('field_id.name')
        return set(mapping_field_names) & set(vals.keys())

    def _get_vals_with_prohibited_update(self, vals):
        mapping = self.env['bus.object.mapping'].get_mapping(self._name)
        if not mapping.is_importable or not mapping.update_prohibited:
            return None
        mapping_field_names = mapping.field_ids.mapped('field_id.name')
        return list(set(mapping_field_names) & set(vals.keys()))

    @api.model
    def create(self, vals):
        vals['write_date_bus'] = fields.Datetime.now()
        return super(BusSynchronizedModelAbstract, self).create(vals)

    @api.multi
    def write(self, vals):
        # do not update write_date_bus if the update comes from synchro to avoid infinite loop of sync diff
        if not self.env.context.get('bus_receive_transfer_external_key', False) and\
                self._vals_contains_a_mapped_exported_field(vals):
            vals['write_date_bus'] = fields.Datetime.now()

        if not self.env.user.is_bus_user:
            fields_prohibited = self._get_vals_with_prohibited_update(vals)
            if fields_prohibited:
                raise exceptions.except_orm(
                    _(u"Error"),
                    _(u"Fields %s are tagged with update prohibited by bus configuration "
                      u"and can't be updated") % fields_prohibited)
        return super(BusSynchronizedModelAbstract, self).write(vals)
