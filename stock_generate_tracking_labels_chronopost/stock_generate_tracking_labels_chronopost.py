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


class TrackingGenerateLabelsWizardChronopost(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    @api.multi
    def generate_one_label_for_all_packages(self):
        result = super(TrackingGenerateLabelsWizardChronopost, self).generate_one_label_for_all_packages()
        self.ensure_one()
        if self.transporter_id == self.env.ref('base_delivery_tracking_chronopost.transporter_chronopost'):
            print 'Chronopost'
            if self.package_ids:
                packages_data = []
                for package in self.package_ids:
                    packages_data += [{
                        'weight': package.delivery_weight,
                        'insured_value': 0,
                        'cod_value': 0,
                        'custom_value': 0,
                        'height': 0,
                        'lenght': 0,
                        'width': 0,
                    }]
                self.with_context(packages_data=packages_data).generate_label()
        return result
