# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import http, models
from odoo.http import request


class TrainingSitting(models.Model):
    _inherit = 'training.sitting'

    def add_sitting_values_for_portal(self, values):
        self.ensure_one()
        values['attachment_convocation_count'] = self.env['training.sitting.convocation.sent'].search_count([
            ('sitting_id', '=', self.id),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])

        if values['attachment_convocation_count']:
            values['attachment'] = self.env['training.sitting.convocation.sent'].search([
                ('sitting_id', '=', self.id),
                ('partner_id', '=', self.env.user.partner_id.id),
            ])
        return values


class SittingPortal(CustomerPortal):

    @http.route('/sittings', type='http', auth='user', website=True)
    def display_sittings_list(self):
        values = super(SittingPortal, self)._prepare_portal_layout_values()
        values['sittings'] = request.env['training.sitting'].search([
            ('attendee_ids', 'in', request.env.user.partner_id.id),
        ])
        values['page_name'] = u"sittings"
        return request.render('training_portal.portal_sittings_list', values)

    @http.route("/sitting/<model('training.sitting'):sitting>", type="http", auth="user", website=True)
    def display_sitting(self, sitting, **kwargs):
        values = super(SittingPortal, self)._prepare_home_portal_values()
        values = sitting.add_sitting_values_for_portal(values)
        values['sitting'] = request.env['training.sitting'].browse(sitting.id)
        values['session'] = request.env['training.session'].browse(sitting.session_id.id)
        values['page_name'] = 'sessions'
        return request.render('training_portal.portal_sitting', values)
