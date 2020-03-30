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

import json
import requests

from odoo import models, fields, api, _ as _t
from odoo.exceptions import UserError
from odoo.addons.queue_job.job import job

from .avis_verifies_json import _field_ident, _field_comment, _field_std_date, _field_bool


class AvisVerifiesReview(models.Model):
    _inherit = 'avis.verifies.json'
    _name = 'avis.verifies.review'
    _order = 'review_date asc'
    _description = u"Avis vérifié"

    _FIELDS_FROM_JSON = (
        ('state', _field_ident, None),
        ('rate', _field_ident, None),
        ('moderation', _field_comment, 'comment_ids'),
        ('canal', _field_ident, None),
        ('name_shop', _field_ident, 'shop_name'),
        ('id_shop', _field_ident, 'shop_id_av'),
        ('insatisfaction_intervention', _field_bool, None),
        ('sc', _field_bool, None),
        ('sc_insatisfaction', _field_ident, None),
        ('#TC=G', _field_bool, 'tc_g'),
        ('tc_insatisfaction', _field_ident, None),
        ('publish_date', _field_std_date, None),
        ('id_review', _field_ident, 'review_id_av'),
        ('order_ref', _field_ident, None),
        ('review_date', _field_std_date, None),
        ('review', _field_ident, None),
        ('lastname', _field_ident, None),
        ('firstname', _field_ident, None),
        ('order_date', _field_std_date, None),
    )

    state = fields.Integer(u"State")
    rate = fields.Selection([
        ('0', u"Very bad"),
        ('1', u"Bad"),
        ('2', u"Neutral"),
        ('3', u"Correct"),
        ('4', u"Good"),
        ('5', u"Excellent"),
    ], u"Rate", readonly=True)
    canal = fields.Char(u"Canal")
    shop_name = fields.Char(u"Shop name")
    shop_id_av = fields.Integer(u"Shop ID in avis-verifies")
    insatisfaction_intervention = fields.Boolean(u"Intervention insatisfaction")
    sc = fields.Boolean(u"Satisfied with customer service")
    sc_insatisfaction = fields.Char(u"Customer service insatisfaction")
    tc_g = fields.Boolean(u"Satisfied with the commercial technician")
    tc_insatisfaction = fields.Char(u"Commercial technician insatisfaction")
    publish_date = fields.Datetime(u"Publish date")
    review_id_av = fields.Char(u"Review ID in avis-verifies")
    order_ref = fields.Char(u"Order reference")
    review_date = fields.Date(u"Review date")
    review = fields.Text(u"Review")
    lastname = fields.Char(u"Last name")
    firstname = fields.Char(u"First name")
    order_date = fields.Datetime(u"Order date")
    comment_ids = fields.One2many('avis.verifies.comment', 'review_id', u"Answers")
    user_id = fields.Many2one('res.users', u"Vendor")
    author_id = fields.Many2one('res.partner', u"Author")

    _sql_constraints = [
        (
            'unique_review_id_av',
            'UNIQUE(review_id_av)',
            _t(u"review_id_av must be unique"),
        ),
    ]

    @api.model
    def cron_refresh(self):
        desc = _t(u"Refresh avis-verifies reviews")
        return self.with_delay(description=desc).refresh_site_reviews()

    @api.model
    @job(default_channel='root.ir_cron')
    def refresh_site_reviews(self):
        url = self.env['ir.config_parameter'].get_param('avis.verifies.site_reviews_url')

        if not url:
            raise UserError(_t(u"You must specify a site reviews URL in sales configuration in order to refresh "
                               u"avis-verifies' reviews. You can get this URL on avis-verifies' website, at "
                               u"Intégration > Récupérer vos Avis > API Site."))

        ans = requests.get(url)
        if ans.status_code != 200:
            raise UserError(_t(u"The refresh of avis-verifies' site review failed with a code %d: %s") %
                            (ans.status_code, ans.content))

        self._load_from_json(json.loads(ans.content))

    @api.model
    def _load_from_json(self, lst_from_rqt):
        res = self.env[self._name]
        for dct in lst_from_rqt:
            if self.search([('review_id_av', '=', dct.get('id_review'))]):
                continue
            res |= self.create(self.vals_from_json(dct))
        return res

    @api.model
    def name_get(self):
        res = []
        for rec in self:
            full_client_name = ((rec.firstname or u"") +
                                ((rec.firstname and rec.lastname) and u" " or u"") +
                                (rec.lastname or u"")) or _t(u"Anonymous")
            res.append((rec.id, _t(u"Review from %s") % full_client_name))
        return res
