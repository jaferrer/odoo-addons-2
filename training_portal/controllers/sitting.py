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
    def display_session(self, sitting, **kwargs):
        values = super(SittingPortal, self)._prepare_home_portal_values()
        values['sitting'] = request.env['training.sitting'].browse(sitting.id)
        values['page_name'] = 'sittings'
        return request.render('training_portal.portal_sitting', values)
