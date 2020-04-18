# Copyright 2015 Guewen Baconnier
# Copyright 2016 Lorenzo Battistini - Agile Business Group
# Copyright 2016 Alessio Gerace - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.delivery_tracking.models.delivery_carrier_provider import _PROVIDER
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    delivery_carrier_ok = fields.Boolean("Is a delivery Carrier Package")


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    delivery_package_ok = fields.Boolean("Use Delivery Package")

    @api.onchange('delivery_package_ok')
    def _onchange_delivery_package_ok(self):
        if self.delivery_package_ok:
            self.show_entire_pack = True
            self.show_operations = True


class StockPackageLevel(models.Model):
    _inherit = 'stock.package_level'

    delivery_package_id = fields.Many2one('delivery.carrier.provider.package', "Delivery Package")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_delivery_package_ok = fields.Boolean("Use Delivery Package", related='picking_type_id.delivery_package_ok',
                                                 readonly=True)

    delivery_package_id = fields.Many2one('delivery.carrier.provider.package', "Delivery Package")

    @api.multi
    def action_put_in_package(self):
        for rec in self:
            rec.package_level_ids.write({'delivery_package_id': rec.delivery_package_id.id})


class DeliveryCarrierProvider(models.Model):
    _inherit = 'delivery.carrier.provider'

    # TODO filter to only see delivery_carrier_ok = false
    packaging_ids = fields.One2many('product.packaging', 'provider_id', "Packaging",
                                    domain=[('delivery_carrier_ok', '=', False)])
    delivery_packaging_ids = fields.One2many('product.packaging', 'provider_id', "Delivery Packaging",
                                             domain=[('delivery_carrier_ok', '=', True)])

    @api.model_create_multi
    def create(self, val_list):
        results = super(DeliveryCarrierProvider, self).create(val_list)
        results._create_default_package()
        return results

    @api.multi
    def write(self, vals):
        res = super(DeliveryCarrierProvider, self).write(vals)
        self._create_default_package()
        return res

    @api.multi
    def _create_default_package(self):
        for rec in self:
            if not rec.delivery_packaging_ids:
                self.env['product.packaging'].create({
                    'name': _("Default Delivery Package") + " - " + rec.name,
                    'package_carrier_type': rec.carrier,
                    'delivery_carrier_ok': True
                })

    @api.multi
    def generate_delivery_package(self, force_packaging=None):
        self.ensure_one()
        default_packaging = force_packaging or self.delivery_packaging_ids[:1]
        if default_packaging:
            return self.env['delivery.provider.package']._get_action_model(
                default_provider_id=self.id,
                default_packaging_id=default_packaging.id,
            )
        raise UserError(_("Your Delivery Provider don't have any Delivery Package"))


class StockPickingPackagePreparation(models.Model):
    _name = 'delivery.carrier.provider.package'
    _description = 'Package of Delivery Provider'
    _inherit = ['mail.thread']

    FIELDS_STATES = {'done': [('readonly', True)],
                     'in_pack': [('readonly', True)],
                     'cancel': [('readonly', True)]}

    @api.model
    def _default_company_id(self):
        company_model = self.env['res.company']
        return company_model._company_default_get(self._name)

    provider_id = fields.Many2one('delivery.carrier.provider', "Provider", required=True)
    carrier_code = fields.Selection(_PROVIDER, string="Provider Code", related='provider_id.carrier', store=True)
    provider_image = fields.Binary("Image", related='provider_id.image')
    name = fields.Char("Name", required=True)
    packaging_id = fields.Many2one('product.packaging', "Packaging", states=FIELDS_STATES)

    state = fields.Selection([
        ('cancel', 'Cancel'),
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('done', 'Done'),
    ], "State", default='draft', compute="_compute_data_from_package_level", store=True)

    picking_ids = fields.Many2many('stock.picking', string="Transfers", compute='_compute_picking_ids')
    picking_count = fields.Integer("#Picking", compute='_compute_picking_ids')
    package_count = fields.Integer("#Package", compute='_compute_package_count')
    date_done = fields.Datetime("Shipping Date", compute='_compute_data_from_package_level', store=True)
    company_id = fields.Many2one('res.company', "Company", required=True, index=True, states=FIELDS_STATES,
                                 default=_default_company_id)
    package_level_ids = fields.One2many('stock.package_level', 'delivery_package_id')
    comment = fields.Text()
    weight = fields.Float("Weight", compute='_compute_weight',
                          help="The weight is computed when the preparation is done.")

    @api.multi
    def _compute_package_count(self):
        groupby = fields = ['delivery_package_id']
        res = self.env['stock.package_level'].read_group([('delivery_package_id', 'in', self.ids)], fields, groupby)
        res = {it['delivery_package_id'][0]: it['delivery_package_id_count'] for it in res if it['delivery_package_id']}
        for rec in self:
            rec.package_count = res.get(rec.id, 0)

    @api.multi
    @api.depends('package_level_ids')
    def _compute_picking_ids(self):
        for rec in self:
            all_picking = self.env['stock.picking']
            for package_level in rec.package_level_ids:
                all_picking |= package_level.picking_id
            rec.picking_ids = all_picking
            rec.picking_count = len(all_picking)

    @api.multi
    @api.depends('package_level_ids', 'package_level_ids.picking_id.state')
    def _compute_data_from_package_level(self):
        for rec in self:
            all_picking = rec.picking_ids
            picking_state = all_picking.mapped('state')
            state = 'draft'
            if all_picking:
                if all(state == 'cancel' for state in picking_state):
                    state = 'cancel'
                if all(state == 'done' for state in picking_state):
                    state = 'done'
            rec.date_done = all_picking and min(pick.date_done for pick in all_picking) or False
            rec.weight = all_picking and sum(pick.shipping_weight for pick in all_picking) or 0
            rec.state = state

    @api.multi
    def action_done(self):
        self.picking_ids.action_done()

    @api.multi
    def action_cancel(self):
        if any(rec.state == 'done' for rec in self):
            raise UserError(_('Cannot cancel a done package delivery.'))
        self.picking_ids.action_cancel()
