# -*- coding: utf8 -*-
#
#    Copyright (C) 2015 NDP Systèmes (<http://www.ndp-systemes.fr>).
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


from openerp import models, api
from openerp.exceptions import UserError


class TrackingGenerateLabelsWizardColissimo(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_one_label_for_all_packages(self):
        result = super(TrackingGenerateLabelsWizardColissimo, self).generate_one_label_for_all_packages()
        self.ensure_one()
        if self.transporter_id == self.env.ref('base_delivery_tracking_colissimo.transporter_colissimo'):
            raise UserError(u"Service indisponible pour Colissimo")
        return result
