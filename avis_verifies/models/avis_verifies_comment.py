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

from odoo import models, fields, api

from .avis_verifies_json import _field_ident, _field_iso8601_date, _field_origin


class AvisVerifiesComment(models.Model):
    _inherit = 'avis.verifies.json'
    _name = 'avis.verifies.comment'
    _order = 'date asc'
    _description = u"Comment"

    _FIELDS_FROM_JSON = (
        ('comment_date', _field_iso8601_date, 'date'),
        ('comment_origin', _field_origin, 'origin'),
        ('comment', _field_ident, None),
    )

    review_id = fields.Many2one('avis.verifies.review', u"Review", required=True)
    date = fields.Date(u"Date")
    origin = fields.Selection([
        ('vendor', u"Vendor"),
        ('client', u"Client")
    ], u"Origin")
    comment = fields.Char(u"Comment", readonly=True)
    author_id = fields.Many2one('res.partner', u"Author", compute='_compute_author_id', store=True)

    @api.multi
    @api.depends('origin', 'review_id', 'review_id.user_id', 'review_id.user_id.partner_id', 'review_id.author_id')
    def _compute_author_id(self):
        for rec in self:
            if rec.origin == 'vendor':
                rec.author_id = rec.review_id.user_id.partner_id
            elif rec.origin == 'client':
                rec.author_id = rec.review_id.author_id
