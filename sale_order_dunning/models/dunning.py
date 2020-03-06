# -*- coding: utf8 -*-
#
#    Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
import datetime
from odoo import fields, models, api, _, osv


class SaleOrderRelanceConfig(models.Model):
    _name = 'sale.order.dunning.type'

    def _get_domain_mail_template(self):
        return [('model_id', '=', self.env.ref('sale_order_dunning.model_sale_order_dunning').id)]

    name = fields.Char(required=True, string="Name")
    number = fields.Integer("Dunning number", default=1, required=True)
    sequence_id = fields.Many2one('ir.sequence', string="Sequence")
    report_id = fields.Many2one('ir.actions.report.xml', string="Report",
                                domain=[('model', '=', 'sale.order.dunning')], required=True)
    mail_template_id = fields.Many2one('mail.template', string="Mail Template", domain=_get_domain_mail_template,
                                       required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)

    @api.multi
    def _get_dunning_name(self):
        return self.ensure_one().sequence_id and self.sequence_id._next() or ""

    _sql_constraints = [
        ('dunning_number_unique', 'unique (number, company_id)', u"The Dunning number must be unique per company !"),
    ]


class SaleOrderRelance(models.Model):
    _name = 'sale.order.dunning'
    _inherit = ['mail.thread']
    _description = u"Sale Order Dunning"
    _order = 'id DESC'

    name = fields.Char(u"Name")
    date_done = fields.Date(u"Dunning date done", readonly=True)
    state = fields.Selection([
        ('draft', u"Draft"),
        ('send', u"Sent"),
        ('cancel', u"Cancel"),
        ('done', u"Done")], string=u"State", readonly=True, default='draft', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string=u"Partner")
    company_id = fields.Many2one('res.company', string=u"Company", default=lambda self: self.env.user.company_id)
    dunning_type_id = fields.Many2one('sale.order.dunning.type', string=u"Dunning Type")
    report_id = fields.Many2one('ir.actions.report.xml', string=u"Report", related='dunning_type_id.report_id',
                                readonly=True)
    sequence_id = fields.Many2one('ir.sequence', related='dunning_type_id.sequence_id', readonly=True)
    mail_template_id = fields.Many2one('mail.template', string=u"Mail Template",
                                       related='dunning_type_id.mail_template_id', readonly=True)
    order_ids = fields.Many2many('sale.order', string=u"Sale Orders")
    folder_id = fields.Many2one('folder', string=u"Dossier")
    amount_total_signed = fields.Float(u"Total", compute='_compute_amounts')
    note = fields.Text(u"Notes")
    user_id = fields.Many2one('res.users', u"Responsible")

    @api.multi
    def _compute_amounts(self):
        for rec in self:
            amount = 0
            for order in rec.order_ids:
                amount += order.amount_total
            rec.amount_total_signed = amount

    @api.model
    def _get_existing_dunning(self, order_id, dunning_config_id):
        return self.search(self._get_existing_dunning_domain(order_id, dunning_config_id))

    @api.multi
    def action_done(self):
        self.write({'state': 'done'})
        next_date = fields.Datetime.to_string(datetime.datetime.now() + datetime.timedelta(days=7))
        self.order_ids.write({'date_next_dunning': next_date})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def _get_existing_dunning_domain(self, order_id, dunning_type_id):
        return [
            ('partner_id', '=', order_id.partner_id.id),
            ('dunning_type_id', '=', dunning_type_id.id),
            ('company_id', '=', order_id.company_id.id),
            ('state', '=', 'draft'),
        ]

    @api.multi
    def action_print_dunning(self):
        self.ensure_one()
        res = self.env['report'].with_context(active_ids=self.ids).get_action(self, self.report_id.report_name)
        self.write({
            'state': 'send',
            'date_done': fields.Date.today(),
        })
        return res

    @api.multi
    def action_send_mail(self):
        self.ensure_one()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model=self._name,
            default_res_id=self.id,
            default_composition_mode='comment',
            default_template_id=self.mail_template_id.ensure_one().id,
        )
        ctx.update(self._default_dict_send_mail_action())
        return {
            'name': _(u"Send a message"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _default_dict_send_mail_action(self):
        return {'final_dunning_state': 'send'}

    @api.multi
    def _get_action_view(self):
        if len(self.ids) > 1:
            ctx = dict(self.env.context,
                       search_default_group_partner_id=True,
                       search_default_group_dunning_type_id=True)
            res = {
                'name': _(u"Dunning"),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order.dunning',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'domain': [('id', 'in', self.ids)]
            }

        else:
            res = {
                'name': self.name,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref("sale_order_dunning.sale_order_dunning_form_view").id,
                'res_model': 'sale.order.dunning',
                'res_id': self.id,
                'type': 'ir.actions.act_window',
            }

        return res

    @api.model
    def cron_sale_order_dunning_update(self):
        """Si le devis dépasse la date d'échéance, alors une relance se créé.

        Jusqu'à 6 relances pour 2 états chacuns: sent et recorded."""
        orders = self.env['sale.order'].search([
            ('state', 'in', ['sent', 'recorded']),
            ('date_next_dunning', '<', fields.Datetime.to_string(datetime.datetime.now()))
        ])
        for order in orders:
            dunnings = self.env['sale.order.dunning'].search([('order_ids', '=', order.id)])
            last_dunning = self.env['sale.order.dunning']
            for dunning in dunnings:
                if dunning.dunning_type_id.number > last_dunning.dunning_type_id.number and dunning.state != 'cancel':
                    last_dunning = dunning
            if ((not last_dunning) or
                    (last_dunning.dunning_type_id.number < 12 and last_dunning.state in ['done', 'cancel'])):
                next_number = last_dunning.dunning_type_id.number + 1
                dunning_type = self.env['sale.order.dunning.type'].search([('number', '=', next_number)])
                self.env['sale.order.dunning'].create({
                    'name': u"Relance" + u"-" + order.name + u"-" + str(next_number),
                    'order_ids': [(6, 0, [order.id])],
                    'partner_id': order.partner_id.id,
                    'user_id': self.env.user.id,
                    'dunning_type_id': dunning_type.id,
                    'folder_id': order.folder_id.id,
                })


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_default_date_next_dunning(self):
        date = datetime.datetime.now() + datetime.timedelta(days=7)
        return fields.Datetime.to_string(date)

    sale_order_dunning_ids = fields.Many2many('sale.order.dunning', string=u"Dunnings")
    dunning_number = fields.Integer(u"Number of Dunning send", compute='_compute_dunning_number')
    date_next_dunning = fields.Datetime(u"Date de prochaine relance", default=_get_default_date_next_dunning)

    @api.multi
    def _compute_dunning_number(self):
        for rec in self:
            rec.dunning_number = len(rec.sale_order_dunning_ids.filtered(lambda it: it.state in ['send', 'done']))

    @api.multi
    def action_create_dunning(self):
        return self._create_dunning()._get_action_view()

    @api.multi
    def _no_next_dunning(self):
        raise osv.osv.except_orm(_(u"Error !"), _(u"No next Dunning Type for the sale order %s" % self.number))

    @api.multi
    def _validate_to_create_dunning(self):
        if self.state not in ['sent', 'recorded']:
            raise osv.osv.except_orm(
                _(u"Error !"), _(u"You can't create a Dunning on a sale order which is not sent or recorded")
            )

    @api.multi
    def _get_next_dunning_type(self):
        dunning_type_ids = self.sale_order_dunning_ids.filtered(lambda it: it.state == 'send').mapped('dunning_type_id')
        return self.env['sale.order.dunning.type'].search(
            [('id', 'not in', dunning_type_ids.ids), ('company_id', '=', self.company_id.id)],
            order='number asc', limit=1)

    @api.multi
    def _prepare_sale_order_dunning(self, dunning_type_id):
        self.ensure_one()
        return {
            'dunning_type_id': dunning_type_id.id,
            'sale_order_ids': [(4, self.id, {})],
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id,
            'name': dunning_type_id._get_dunning_name()
        }

    @api.multi
    def action_sale_order_paid(self):
        to_sign_orders = self.filtered(lambda order: order.state != 'sent')
        for rec in to_sign_orders:
            for dunning in rec.sale_order_dunning_ids:
                if dunning.state == 'draft':
                    rec.sale_order_dunning_ids = [(3, dunning.id)]
        return super(SaleOrder, self).action_sale_order_paid()

    @api.multi
    def _create_dunning(self):
        result = self.env['sale.order.dunning']
        for rec in self:
            rec._validate_to_create_dunning()
            next_dunning_type = rec._get_next_dunning_type()
            if next_dunning_type:
                existing_dunning = self.env['sale.order.dunning']._get_existing_dunning(rec, next_dunning_type)
                if existing_dunning:
                    existing_dunning.order_ids = [(4, rec.id, {})]
                else:
                    existing_dunning = self.env['sale.order.dunning'].create(
                        rec._prepare_sale_order_dunning(next_dunning_type))
                result |= existing_dunning
            else:
                rec._no_next_dunning()
        return result

    @api.model
    def compute_dunning_sale_order(self):

        days = self.env.user.company_id.sending_validity_duration

        limite_validate_of_sent = datetime.datetime.now() - datetime.timedelta(days=days)

        orders_with_send_dunning = self.env['sale.order.dunning'].search(
            [('state', '=', 'send'), ('date_done', '>=', limite_validate_of_sent)]).mapped('order_ids')
        orders_dunning_to_create = self.search(
            [('state', '=', 'open'), ('id', 'not in', orders_with_send_dunning.ids)])
        orders_dunning_to_create._create_dunning()


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self.env.context or {}
        if context.get('default_model') == 'sale.order.dunning' \
                and context.get('default_res_id', -1) > 0 \
                and context.get('final_dunning_state'):
            self.env['sale.order.dunning'].browse(context['default_res_id']).write({
                'state': context.get('final_dunning_state'),
                'date_done': fields.Date.today(),
            })
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
