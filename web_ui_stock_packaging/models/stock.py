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
from openerp import models, api, fields


class WebUiError(Exception):
    pass


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_picking_info_by_name(self, name):
        """
        On peut rechercher un picking, soit par le nom de son groupe d'appro, soit par son nom.
        """
        name = name.strip()
        picking = self.env['stock.picking'].search([('name', '=ilike', name)])
        if not picking:
            raise WebUiError(name, "Aucun transfert trouvé")
        if len(picking) > 1:
            raise WebUiError(name, "Plusieurs transferts ont été trouvé: %s" % ", ".join(picking.mapped('name')))
        if picking.state not in ['assigned', 'done']:
            raise WebUiError(
                name,
                "L'état est %s alors que il devrait être Disponible ou Terminé" % picking._translate_state_label()
            )
        return picking.web_ui_get_picking_info_one(name)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def web_ui_check_action_allowed(self, action="faire cette action", raise_error=True, other_name=None):
        self.ensure_one()
        not_allowed = self.state == 'cancel'
        reason = "annulé"
        name = other_name or self.name
        msg = u"Vous ne pouvez pas %s le %s car il est %s" % (action, name, reason)
        if not_allowed and raise_error:
            raise WebUiError(name, msg)
        return not_allowed and msg or ""

    @api.multi
    def web_ui_get_picking_info_one(self, other_name=None):
        self.ensure_one()
        return {
            'id': self.id,
            'name': other_name or self.name,
            'carrier_id': self.carrier_id.delivery_type,
            'owner_id': self.owner_id.id,
            'owner_id_name': self.owner_id.display_name,
            'state': self.state,
            'state_label': self._translate_state_label(),
            'package_count': len(self.move_line_ids_without_package.mapped('result_package_id').ids) or 1,
            'operations_todo': len(
                self.move_line_ids_without_package.filtered(lambda it: not it.result_package_id).ids),
            'not_allowed_reason': self.web_ui_check_action_allowed("mettre en colis", False, other_name=other_name),
        }

    @api.multi
    def _translate_state_label(self):
        self.ensure_one()
        dict_state_label = dict(self._fields['state'].selection)
        term = dict_state_label[self.state]
        return self.env['ir.translation']._get_source("stock.picking,state", 'selection', self.env.user.lang, term)

    @api.multi
    def web_ui_get_data_move_lines_todo(self):
        self.ensure_one()
        domain = [('picking_id', '=', self.id), ('result_package_id', '=', False)]
        return {
            'package_names': self.move_line_ids_without_package.mapped('result_package_id').name_get(),
            'operations': [{
                'uuid': move_line.id,
                'product_id': move_line.product_id.id,
                'product_name': move_line.product_id.display_name,
                'unit_weight': move_line.product_id.weight,
                'qty_todo': move_line.product_qty,
                'qty_done': move_line.qty_done,
            } for move_line in self.env['stock.move.line'].search(domain)]
        }

    @api.multi
    def web_ui_set_operations_qty(self, move_lines):
        self.ensure_one()
        self.web_ui_check_action_allowed("mettre en colis")
        for move_line_id, qty in move_lines:
            self.env['stock.move.line'].browse(move_line_id).qty_done = qty

        wizard = self._get_picking_pack_wizard(True)
        pack = wizard.pack_wizard_validate_button()
        detail = self.web_ui_get_data_move_lines_todo()
        detail['new_pack'] = {
            'package_weight': wizard.poids,
            'package_name': pack.display_name,
            'package_id': pack.id,
        }
        return detail

    @api.multi
    def web_ui_print_label(self, packaging_computer_id=None):
        self.ensure_one()
        self.web_ui_check_action_allowed("imprimer l'étiquette")
        packop_without_package = self.pack_operation_ids.filtered(lambda packop: not packop.result_package_id)
        if packop_without_package:
            packop_without_package._set_product_qty_in_qty_done()
            wizard = self._get_picking_pack_wizard(True)
            wizard.pack_wizard_validate_button()

        if not self.binary_label:
            data = self._get_tracking_labels_wizard_data()
            wizard_label = self.env['generate.tracking.labels.wizard'].create(data)._trigger_onchange()
            wizard_label.generate_one_label_for_all_packages()

        self.action_done()

        self._send_label_to_printer_bot(packaging_computer_id)
        return True

    @api.multi
    def _send_label_to_printer_bot(self, packaging_computer_id):
        if packaging_computer_id:
            packaging_computer = self.env['poste.packing'].browse(packaging_computer_id)
            printer_bot_messages = []
            label_domain = [('res_id', 'in', self.ids), ('res_model', '=', self._name)]
            for label in self.env['ir.attachment'].search(label_domain + [('res_field', '=', 'binary_label')]):
                filename = 'IMPRESSION_ETIQUETTE.pdf'
                if self.partner_id.country_id.force_custom_declaration:
                    filename = 'A4_DOCUMENT_EXPEDITION.pdf'
                else:
                    code = self.move_lines[0].transporter_code
                    type_produit = self.get_produit(self.owner_id, code)[1]
                    if type_produit.output_printing_type_default_id.print_on_a4:
                        filename = 'A4_DOCUMENT_EXPEDITION.pdf'

                printer_bot_messages.append([
                    (self.env.cr.dbname, 'request.async.print'),
                    {
                        'active_id': label.res_id,
                        'active_model': self._name,
                        'user_id': self.env.user.id,
                        'packing': packaging_computer.code,
                        'attachment_id': label.id,
                        'attachment_name': filename
                    }
                ])

            for label in self.env['ir.attachment'].search(label_domain + [('res_field', '=', 'invoice_label')]):
                for i in range(0, 2):
                    printer_bot_messages.append([
                        (self.env.cr.dbname, 'request.async.print'),
                        {
                            'active_id': label.res_id,
                            'active_model': self._name,
                            'user_id': self.env.user.id,
                            'packing': packaging_computer.code,
                            'attachment_seq': i,
                            'attachment_id': label.id,
                            'attachment_name': 'A4_INVOICE.pdf'
                        }
                    ])

            self.env['bus.bus'].sendmany(printer_bot_messages)


class PostePacking(models.Model):
    _name = 'poste.packing'
    _description = "Poste Packing"

    name = fields.Char("Nom")
    description = fields.Char("Description")
    code = fields.Char("Code")
