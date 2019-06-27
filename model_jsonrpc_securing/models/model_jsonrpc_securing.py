# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, exceptions


class ModelJsonrpcSecuring(models.AbstractModel):
    _name = 'model.jsonprc.securing'

    @api.model
    def create(self, vals):
        raise exceptions.AccessError(u"Not allowed to create a record for this model : %s, see Model Jsonrpc securing "
                                     u"module for more details." % self._name)

    @api.model
    def _secure_create(self, vals):
        return super(ModelJsonrpcSecuring, self).create(vals)

    @api.multi
    def write(self, vals):
        raise exceptions.AccessError(u"Not allowed to edit a record for this model : %s, see Model Jsonrpc securing "
                                     u"module for more details." % self._name)

    @api.multi
    def _secure_write(self, vals):
        return super(ModelJsonrpcSecuring, self).write(vals)

    @api.multi
    def unlink(self):
        raise exceptions.AccessError(u"Not allowed to remove a record for this model : %s, see Model Jsonrpc securing "
                                     u"module for more details" % self._name)

    @api.multi
    def _secure_unlink(self):
        return super(ModelJsonrpcSecuring, self).unlink()
