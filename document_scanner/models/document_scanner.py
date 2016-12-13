from openerp import fields, models, api, _
import openerp
from openerp.http import request


class Scanner(models.Model):
    _name = 'scanner.info'

    name = fields.Char(u"Name")

    @api.model
    def register(self, name):
        if not self.search([('name', '=', name)]):
            self.create({'name': name})


class DocumentScannerUser(models.Model):
    _inherit = "res.users"

    scanner_id = fields.Many2one('scanner.info', string=u"Actual Scanner")

    def __init__(self, pool, cr):
        init_res = super(DocumentScannerUser, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['scanner_id'])
        return init_res


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
            'scan_name': (user.scanner_id.name or '').lower().replace(' ', '_')
        }
        self.env['bus.bus'].sendone(channel=channel, message=msg)
        return {'scan_name': user.scanner_id.name}

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
