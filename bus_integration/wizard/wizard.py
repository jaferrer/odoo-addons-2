# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, api, fields


class Wizard(models.Model):
    _name = "sirail.trt.msg.synchro"

    model = fields.Many2one("object.mapping", string=u"Modèle à exporter", required=True)
    bus_batch_id = fields.Many2one("busextend.backend.batch", string=u"batch_id", required=True)
    domain = fields.Char(u"Domaine", required=True, help=u"""
    You can see the additional object/functions in the model busextend.backend.batch.
    You can acces to : relativedelta, self, context.
    For datetime use shorcut date, date_to_str to translate dates.
    last_send_date to get the last date of dispatch.""")
    code = fields.Char(string=u"Code", required=True)
    chunk = fields.Integer(u"Taille du chunk d'export")

    _sql_constraints = [('code_uniq_by_synchro', 'unique (code)',
                         u"Impossible d'avoir deux lignes de synchro avec le même code")]

    @api.multi
    def write(self, vals):
        self.bus_batch_id.write({
            'commentaire': u"Model : %s Domain : %s" % (self.model.name, self.domain),
            'model': self.model.name,
        })
        return super(Wizard, self).write(vals)
