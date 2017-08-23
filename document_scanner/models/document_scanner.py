# -*- coding: utf8 -*-
#
#    Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
from openerp import fields, models, api, _
import openerp
from openerp.http import request


class ScannerInfoDpi(models.Model):
    _name = 'scanner.info.dpi'

    name = fields.Char(u"Name")

    @api.model
    def register(self, name):
        if not self.search([('name', '=', name)]):
            self.create({'name': name})


class ScannerInfoColor(models.Model):
    _name = 'scanner.info.color'

    name = fields.Char(u"Name")

    @api.model
    def register(self, name):
        if not self.search([('name', '=', name)]):
            self.create({'name': name})


class Scanner(models.Model):
    _name = 'scanner.info'

    name = fields.Char(u"Name")

    def _get_default_color_id(self):
        return self.env.ref('document_scanner.scanner_info_color_color')

    def _get_default_dpi_id(self):
        return self.env.ref('document_scanner.scanner_info_resolution_300_dpi')

    color_id = fields.Many2one('scanner.info.color', u"Color", default=_get_default_color_id, required=True)
    dpi_id = fields.Many2one('scanner.info.dpi', u"DPI", default=_get_default_dpi_id, required=True)

    @api.model
    def register(self, name):
        if not self.search([('name', '=', name)]):
            self.create({'name': name})


class DocumentScannerUser(models.Model):
    _inherit = "res.users"

    scanner_id = fields.Many2one('scanner.info', string=u"Actual Scanner")

    def __init__(self, pool, cr):
        super(DocumentScannerUser, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['scanner_id'])


class IrAttachmentScanner(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def scan(self, ctx):
        active_id = ctx['active_id']
        active_model = ctx['active_model']
        user = self.env.user
        if not user.has_group('document_scanner.group_scanner_user'):
            return {"error": _("You are not allowed to scan a document")}
        if not user.scanner_id.name:
            return {"error": _("You need to defined a scanner in your settings")}
        channel = (self.env.cr.dbname, 'request.scanner')
        msg = {
            'active_id': active_id,
            'active_model': active_model,
            'user_id': user.id,
            'scan_name': (user.scanner_id.name or '').lower().replace(' ', '_'),
            'scan_color_info': user.scanner_id.color_id.name,
            'scan_dpi_info': user.scanner_id.dpi_id.name,
            'scan_duplex': ctx.get('scan_duplex', False),
        }
        self.env['bus.bus'].sendone(channel=channel, message=msg)
        return {'scan_name': user.scanner_id.name}

    @api.model
    def scan_duplex(self, ctx):
        ctx['scan_duplex'] = True
        return self.scan(ctx)

    @api.multi
    def check(self, mode, values=None):
        if not self.env.user.has_group('document_scanner.bot_ir_attachment'):
            super(IrAttachmentScanner, self).check(mode, values=values)

    @api.cr_uid_context
    def __get_partner_id(self, cr, uid, res_model, res_id, context=None):
        if not self.env.user.has_group('document_scanner.bot_ir_attachment'):
            return super(IrAttachmentScanner, self).__get_partner_id(cr, uid, res_model, res_id, context=context)
        return False


class ImBusScanner(models.Model):
    _inherit = 'bus.bus'

    @api.model
    def get_last(self):
        self.env.cr.execute("SELECT max(id) from bus_bus")
        return self.env.cr.fetchone()


class DocumentScannerBus(openerp.addons.bus.bus.Controller):
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels.append((request.db, 'request.scanner'))
        return super(DocumentScannerBus, self)._poll(dbname, channels, last, options)
