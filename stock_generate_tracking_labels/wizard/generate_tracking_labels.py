# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import os
import tempfile
import base64

from PyPDF2 import PdfFileMerger, PdfFileReader

from openerp import models, fields, api, _ as _t
from openerp.exceptions import UserError


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

PATH_BOT = tempfile.gettempdir() + os.sep + 'merger_bot'
PATH_TMP = PATH_BOT + os.sep + 'tmp'
if not os.path.exists(PATH_TMP):
    os.makedirs(PATH_TMP)


class TrackingGenerateLabelsWizard(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    picking_id = fields.Many2one('stock.picking', string="Stock Picking", required=True)
    package_ids = fields.Many2many('stock.quant.package', string="Packages")
    packages_defined = fields.Boolean(compute='_compute_packages_defined')

    @api.multi
    def _compute_packages_defined(self):
        for rec in self:
            rec.packages_defined = bool(rec.package_ids)

    @api.multi
    def get_output_file(self):
        if self.direction == 'from_customer' and self.picking_id:
            return _t("Incoming label for picking ") + (self.picking_id.name or '') + ".pdf"
        elif self.direction == 'to_customer' and self.picking_id:
            return _t("Outgoing label for picking ") + (self.picking_id.name or '') + ".pdf"

    @api.multi
    def create_attachment(self, list_files=None):
        result = super(TrackingGenerateLabelsWizard, self).create_attachment(list_files=list_files)
        outputfile = self.get_output_file()
        if self.picking_id:
            final_encoded_data = False
            if len(list_files) > 1:
                filenames = []
                for index in range(0, len(list_files)):
                    filename = PATH_TMP + os.sep + "tmp_pdf_label_%s.pdf" % str(index)
                    filenames.append(filename)
                    with file(filename, 'wb') as f:
                        f.write(list_files[index])
                if filenames:
                    myobj = StringIO()
                    merger = PdfFileMerger()
                    for filename in filenames:
                        with file(filename, 'rb') as partial_file:
                            merger.append(PdfFileReader(partial_file))
                    merger.write(myobj)
                    final_encoded_data = base64.encodestring(myobj.getvalue())
                    merger.close()
                    myobj.close()
                    self.picking_id.binary_label = False
                    if self.picking_id.tracking_ids:
                        self.picking_id.tracking_ids.unlink()
            elif len(list_files) == 1:
                final_encoded_data = base64.encodestring(list_files[0])
            if final_encoded_data:
                self.picking_id.write({
                    'binary_label': final_encoded_data,
                    'data_fname': outputfile,
                })
        return result

    @api.multi
    def generate_label(self):
        result = super(TrackingGenerateLabelsWizard, self).generate_label()
        if self.picking_id and self.transporter_id:
            tracking_numbers = result
            if tracking_numbers and self.save_tracking_number:
                for tracking_number in tracking_numbers:
                    self.env['tracking.number'].create({
                        'picking_id': self.picking_id and self.picking_id.id or False,
                        'name': tracking_number,
                        'transporter_id': self.transporter_id.id,
                    })
                self.picking_id.update_delivery_status()
        return result

    @api.multi
    def get_packages_data_for_quants(self, quants):
        self.ensure_one()
        amount_untaxed = sum([quant.qty * quant.price_unit_untaxed for quant in quants])
        amount_total = sum([quant.qty * quant.price_unit_total for quant in quants])
        custom_declaration = []
        done_products = []
        weight = 0
        for quant in quants:
            if quant.product_id not in done_products:
                if self.generate_custom_declaration and not quant.product_id.hs_code:
                    raise UserError(u"Veuillez renseigner le numéro tarifaire de l'article %s" %
                                    quant.product_id.display_name)
                quants_current_products = self.env['stock.quant'].search([('id', 'in', quants.ids),
                                                                          ('product_id', '=', quant.product_id.id)])
                quantity = sum([sq.qty for sq in quants_current_products])
                # TODO: obtenir importers_reference, office_origin, totalAmount
                weight += quant.product_id.weight * quantity
                custom_declaration += [{
                    'description': quant.product_id.name,
                    'quantity': quantity,
                    'weight': quant.product_id.weight,
                    'value': sum([sq.price_unit_untaxed * sq.qty for sq in quants_current_products]) / quantity,
                    'hs_code': quant.product_id.hs_code,
                    'country_code': self.partner_orig_id.country_id.code or '',
                }]
                done_products += [quant.product_id]
        return [{
            'weight': weight,
            'amount_untaxed': int(amount_untaxed),
            'amount_total': int(amount_total),
            'cod_value': 0,
            'height': 0,
            'lenght': 0,
            'width': 0,
            'custom_declaration': custom_declaration,
            'category': self.content_type_id.code,
            'importers_reference': '',
            'importers_contact': self.partner_orig_id.phone or self.partner_orig_id.mobile or '',
            'office_origin': '',
        }]

    @api.multi
    def get_packages_data(self):
        package_ids = self.env.context.get('package_ids')
        if package_ids:
            packages_data = []
            for package in self.env['stock.quant.package'].browse(package_ids):
                if not package.delivery_weight:
                    raise UserError(u"Veuillez renseigner le poids pour le colis %s" % package.display_name)
                quant_ids = package.get_content()
                quants = self.env['stock.quant'].browse(quant_ids)
                pack = self.get_packages_data_for_quants(quants)
                pack[0]['weight'] = package.delivery_weight
                packages_data += pack

            return packages_data
        elif self.picking_id:
            moved_quants = self.env['stock.quant']
            for move in self.picking_id.move_lines:
                if move.state == 'done':
                    moved_quants += move.quant_ids
            packages_data = self.get_packages_data_for_quants(moved_quants)
        else:
            packages_data = super(TrackingGenerateLabelsWizard, self).get_packages_data()
        return packages_data

    @api.multi
    def get_order_number(self):
        self.ensure_one()
        if self.picking_id.group_id.name:
            return self.picking_id.group_id.name
        return super(TrackingGenerateLabelsWizard, self).get_order_number()

    @api.multi
    def launch_report(self, report):
        if self.picking_id:
            data = {'report_type': 'aeroo'}
            context = self.env.context.copy()
            context['active_model'] = 'generate.tracking.labels.wizard'
            report_result, _ = self.pool.get('ir.actions.report.xml'). \
                render_report(self.env.cr, self.env.user.id, self.ids, report.report_name, data, context)
            self.create_attachment(list_files=[report_result])

    @api.multi
    def get_nb_labels(self):
        nb_labels = super(TrackingGenerateLabelsWizard, self).get_nb_labels()
        if self.env.context.get('package_ids'):
            nb_labels = len(self.env.context['package_ids'])
        return nb_labels

    @api.multi
    def generate_one_label_for_all_packages(self):
        self.ensure_one()
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
            return self.with_context(package_ids=self.package_ids.ids).generate_label()
        else:
            raise UserError(u"Aucun colis trouvé")
