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
from openerp import models, api, _ as _t


class WebUiError(Exception):
    pass


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.multi
    def web_ui_get_picking_info_by_name(self, name):
        name = name.strip()
        picking = self.env['stock.picking'].search([('name', '=ilike', name)]).read(['group_id'], load='no_name')
        if not picking:
            raise WebUiError(name, _t(u"Aucun transfert trouvé"))
        group_id = picking[0]['group_id']
        picking = self.env['stock.picking'].search([('group_id', '=', group_id), ('picking_type_id', '=', self.id)])
        if len(picking) > 1:
            raise WebUiError(name, _t(u"Plusieurs transferts ont été trouvé: %s" % u", ".join(picking.mapped('name'))))
        if picking.state not in ['assigned', 'done']:
            raise WebUiError(
                name,
                _t(u"L'état est %s alors que il devrait être Disponible ou Terminé" % picking._translate_state_label())
            )
        return picking.web_ui_get_picking_info_one(name)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def web_ui_check_action_allowed(self, action=u"faire cette action", raise_error=True, other_name=None):
        self.ensure_one()
        not_allowed = self.pause or self.state == 'cancel'
        reason = self.pause and u"mis en attente" or u"annulé"
        name = other_name or self.name
        msg = u"Vous ne pouvez pas %s le %s car il est %s" % (action, name, reason)
        if not_allowed and raise_error:
            raise WebUiError(name, msg)
        return not_allowed and msg or u""

    @api.multi
    def web_ui_get_picking_info_one(self, other_name=None):
        self.ensure_one()
        return {
            'id': self.id,
            'name': other_name or self.name,
            'transporter_id': self.transporter_move_id.id,
            'transporter_id_name': self.transporter_move_id.display_name,
            'owner_id': self.owner_id.id,
            'owner_id_name': self.owner_id.display_name,
            'state': self.state,
            'state_label': self._translate_state_label(),
            'binary_label': bool(self.binary_label),
            'package_count': len(self.pack_operation_product_ids.mapped('result_package_id').ids) or 1,
            'operations_todo': len(self.pack_operation_product_ids.filtered(lambda it: not it.result_package_id).ids),
            'country_need_cn23': self.country_need_cn23,
            'other_picking': self._get_other_bpick_names(other_name)[self],
            'not_allowed_reason': self.web_ui_check_action_allowed(u"mettre en colis", False, other_name=other_name),
        }

    @api.multi
    def _translate_state_label(self):
        self.ensure_one()
        dict_state_label = dict(self._fields['state'].selection)
        term = dict_state_label[self.state]
        return self.env['ir.translation']._get_source("stock.picking,state", 'selection', self.env.user.lang, term)

    @api.multi
    def web_ui_get_data_stock_operation_todo(self):
        self.ensure_one()
        domain = [('picking_id', '=', self.id), ("result_package_id", "=", False)]
        return {
            'package_names': self.pack_operation_product_ids.mapped('result_package_id').name_get(),
            'operations': [{
                'uuid': packop.id,
                'product_id': packop.product_id.id,
                'product_name': packop.product_id.display_name,
                'unit_weight': packop.product_id.poids or packop.product_id.weight,
                'qty_todo': packop.product_qty,
                'qty_done': packop.qty_done,
                'total_weight': packop.weight,
            } for packop in self.env['stock.pack.operation'].search(domain)]
        }

    @api.multi
    def web_ui_set_operations_qty(self, operations):
        self.ensure_one()
        self.web_ui_check_action_allowed(u"mettre en colis")
        for operation_id, qty in operations:
            self.env['stock.pack.operation'].browse(operation_id).qty_done = qty

        wizard = self._get_picking_pack_wizard(True)
        pack = wizard.pack_wizard_validate_button()
        detail = self.web_ui_get_data_stock_operation_todo()
        detail['new_pack'] = {
            'package_weight': wizard.poids,
            'package_name': pack.display_name,
            'package_id': pack.id,
        }
        return detail

    @api.multi
    def web_ui_print_label(self, packaging_computer_id=None):
        self.ensure_one()
        self.web_ui_check_action_allowed(u"imprimer l'étiquette")
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
