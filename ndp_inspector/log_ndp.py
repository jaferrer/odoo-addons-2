# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from openerp import models, fields, api


class NdpLoggingTime(models.Model):
    _name = 'ndp.logging.time'

    model_name = fields.Char(required=True, readonly=True)
    model_id = fields.Many2one('ir.model', readonly=True)
    method = fields.Char("Le nom de la method", required=True, readonly=True)
    time_take = fields.Float(u"Le temps pris en sec", required=True, readonly=True, group_operator="avg")
    user_id = fields.Many2one('res.users', u"Le user qui a lancé la requete", required=True, readonly=True)
    date_start = fields.Datetime(u"Date de debut de l'appelle", readonly=True)
    date_end = fields.Datetime(u"Date de fin de l'appelle", readonly=True)
    vms = fields.Float(u"Mémoire virtuelle utlisé en %", readonly=True,
                       help="""“Virtual Memory Size”,
     this is the total amount of virtual memory used by the process. On UNIX it matches “top“‘s VIRT column""")
    rss = fields.Float(u"Mémoire réelle utlisé en %", readonly=True,
                       help=""" “Resident Set Size”, this is the non-swapped physical memory 
                       a process has used. On UNIX it matches “top“‘s RES column""")
    type_call = fields.Selection([
        ('call_kw', 'Unconfirmed'),
        ('call_button', 'Cancelled'),
    ], string=u"Type d'appelle", required=True, readonly=True)

    @api.model
    def create_record(self, model_ref, method, date_start, date_end, user_id=False, type_call="call_kw"):
        time_take = (date_end - date_start).total_seconds()
        if time_take >= 5:
            try:
                dict_vals = {"user_id": user_id or 1,
                             "model_name": model_ref,
                             "method": method,
                             "time_take": time_take,
                             "date_start": date_start,
                             "date_end": date_end,
                             "type_call": type_call
                             }

                if all(dict_vals.values()):
                    model = self.env['ir.model'].search_read(fields=["id"], domain=[("model", "=", model_ref)], limit=1)
                    dict_vals["model_id"] = model and model[0] and model[0]["id"] or False
                    self.create(dict_vals)
            except (BaseException):
                pass
