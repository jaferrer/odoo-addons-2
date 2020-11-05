# -*- coding: utf-8 -*-
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import http
from odoo.http import request


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

        values['attachment_count'] = request.env['training.sitting.convocation.sent'].search_count([
            ('sitting_id', '=', sitting.id),
            ('partner_id', '=', request.env.user.partner_id.id),
        ])

        if values['attachment_count']:
            values['attachment'] = request.env['training.sitting.convocation.sent'].search([
                ('sitting_id', '=', sitting.id),
                ('partner_id', '=', request.env.user.partner_id.id),
            ])

        values['sitting'] = request.env['training.sitting'].browse(sitting.id)
        values['session'] = request.env['training.session'].browse(sitting.session_id.id)

        values['page_name'] = 'sessions'
        return request.render('training_portal.portal_sitting', values)
