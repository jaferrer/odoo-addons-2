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

import base64

from openerp import models, fields, api, _


class DeliveryTrackingStockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_defined = fields.Boolean(compute='_compute_tracking_defined', store=True)
    binary_label = fields.Binary(string="Label (binary)")
    tracking_label_attachment = fields.Many2one('ir.attachment', string="Label (attachment)")
    data_fname = fields.Char(string="Label name")

    @api.depends('tracking_ids')
    def _compute_tracking_defined(self):
        for rec in self:
            rec.tracking_defined = bool(rec.tracking_ids)

    @api.multi
    def generate_tracking_labels(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['default_picking_id'] = self.id
        ctx['default_partner_id'] = self.partner_id and self.partner_id.id or False
        if self.picking_type_code == 'incoming':
            ctx['default_direction'] = 'from_customer'
        else:
            ctx['default_direction'] = 'to_customer'
        packages = self.env['stock.quant.package']
        for packop in self.pack_operation_product_ids:
            if packop.result_package_id and packop.result_package_id not in packages:
                packages |= packop.result_package_id
        if packages:
            ctx['default_package_ids'] = [(6, 0, packages.ids)]
            ctx['default_weight'] = sum([pack.weight for pack in packages])
        return {
            'name': _("Generate tracking label for picking %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'generate.tracking.labels.wizard',
            'target': 'new',
            'context': ctx,
        }


class TrackingLabelStockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    tracking_defined = fields.Boolean(compute='_compute_tracking_defined', store=True)
    binary_label = fields.Binary(string="Label (binary)")
    tracking_label_attachment = fields.Many2one('ir.attachment', string="Label (attachment)")
    data_fname = fields.Char(string="Label name")

    @api.depends('tracking_ids')
    def _compute_tracking_defined(self):
        for rec in self:
            rec.tracking_defined = bool(rec.tracking_ids)

    @api.multi
    def generate_tracking_labels(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx['default_partner_id'] = self.partner_id and self.partner_id.id or False
        ctx['default_direction'] = 'to_customer'
        ctx['default_weight'] = sum([pack.weight for pack in self])
        ctx['default_package_ids'] = [(6, 0, self.ids)]
        return {
            'name': _("Generate tracking label for package %s") % self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'generate.tracking.labels.wizard',
            'target': 'new',
            'context': ctx,
        }


class TrackingGenerateLabelsWizard(models.TransientModel):
    _inherit = 'generate.tracking.labels.wizard'

    picking_id = fields.Many2one('stock.picking', string="Stock Picking")
    package_ids = fields.Many2many('stock.quant.package', string="Packages")
    packages_defined = fields.Boolean(compute='_compute_packages_defined')

    @api.depends('package_ids')
    @api.multi
    def _compute_packages_defined(self):
        for rec in self:
            rec.packages_defined = bool(rec.package_ids)

    @api.multi
    def get_output_file(self, direction):
        package = False
        if self.env.context.get('set_package_for_label'):
            package = self.env['stock.quant.package'].browse([self.env.context['set_package_for_label']])
        if direction == 'from_customer':
            if package:
                return _("Incoming label for package ") + (package.name or '') + ".pdf"
            elif self.picking_id:
                return _("Incoming label for picking ") + (self.picking_id.name or '') + ".pdf"
        elif direction == 'to_customer':
            if package:
                return _("Outgoing label for package ") + (package.name or '') + ".pdf"
            elif self.picking_id:
                return _("Outgoing label for picking ") + (self.picking_id.name or '') + ".pdf"

    @api.multi
    def create_attachment(self, outputfile, direction, file=False, pdf_binary_string=False):
        encoded_data = file and base64.encodestring(file) or base64.encodestring(pdf_binary_string)
        result = super(TrackingGenerateLabelsWizard, self).create_attachment(outputfile, direction, file=file,
                                                                             pdf_binary_string=pdf_binary_string)
        if self.picking_id:
            if self.env.context.get('set_package_for_label'):
                self.picking_id.write({'binary_label': False,
                                       'data_fname': False,
                                       'tracking_label_attachment': False})
            else:
                self.picking_id.write({'binary_label': encoded_data,
                                       'data_fname': outputfile})
                self.picking_id.tracking_label_attachment = self.env['ir.attachment'].create({
                    'name': outputfile,
                    'datas': encoded_data,
                    'datas_fname': outputfile,
                    'res_model': 'stock.picking',
                    'res_id': self.picking_id.id
                })
        if self.env.context.get('set_package_for_label'):
            package = self.env['stock.quant.package'].browse([self.env.context['set_package_for_label']])
            package.write({'binary_label': encoded_data,
                           'data_fname': outputfile})
            package.tracking_label_attachment = self.env['ir.attachment'].create({
                'name': outputfile,
                'datas': encoded_data,
                'datas_fname': outputfile,
                'res_model': 'stock.quant.package',
                'res_id': package.id
            })
        return result

    @api.multi
    def generate_label(self):
        tracking_number, save_tracking_number, direction, url = \
            super(TrackingGenerateLabelsWizard, self).generate_label()
        package = False
        if self.env.context.get('set_package_for_label'):
            package = self.env['stock.quant.package'].browse([self.env.context['set_package_for_label']])
        if (self.picking_id or package) and tracking_number and save_tracking_number and self.transporter_id:
            self.env['tracking.number'].create({
                'picking_id': self.picking_id and self.picking_id.id or False,
                'package_id': package and package.id or False,
                'name': tracking_number,
                'transporter_id': self.transporter_id.id,
            })
            self.picking_id.update_delivery_status()
        return tracking_number, save_tracking_number, direction, url

    @api.multi
    def generate_one_label_for_each_package(self):
        self.ensure_one()
        for package in self.package_ids:
            self.weight = package.weight
            self.with_context(set_package_for_label=package.id).generate_label()
