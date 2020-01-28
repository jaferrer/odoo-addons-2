# -*- coding: utf8 -*-
#
#    Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class TcbPushPackOp(models.Model):

    """Table syncronisé avec android, ne traiter les que les picking wave qui possede le Flag START
    et qui fini par END. Il faut bien verifier que la sequence soit complete."""
    _name = 'tcb.push.pack.op'
    _order = 'picking_batch_id, sequence'

    # flag chaque ligner possede un flag
    # un picking wave possede forcement un le flag 'START' avec un numero de sequence a 0
    # ensuite le flag décris l'action réalisé par le pickeur
    # END le picking wave à été valider dans son état par le pickeur.
    # -- la sequence sera forcement la plus haute pour ece picking wave
    flag = fields.Selection([
        ('START', u"Début"),  # Premier flag d'une suite logique de traitement sur un Picking ou une vague
        ('END', u"Fin"),  # Dernier flag d'une suite logique de traitement sur un Picking ou une vague
        ('PACK_OP_DONE', u"Done"),  # Tout c'est bien passé
        ('PACK_OP_SPLIT', u"Split"),  # L'operation de stock a été découpé
        ('PACK_OP_CHG_LOC',
            u"Changement packop d'emplacement"),  # L'operation de stock a été découpé en plusieurs emplacements
        ('PACK_OP_PASS', u"Pass"),  # Le pack op a été passer
    ], string=u"Flag")

    # Id du picking wave concerné, toujours renseigné
    user_id = fields.Many2one('res.users', string=u"Utilisateur", required=True)
    picking_batch_id = fields.Many2one('stock.picking.batch', string=u"Picking Batch")
    picking_batch_user_id = fields.Many2one('res.users', string=u"Responsable Picking Batch",
                                           related='picking_batch_id.user_id')
    picking_batch_state = fields.Selection(string=u"Statut Picking Batch", related='picking_batch_id.state')
    # Id du pack op concerné toujours renseigné sauf lors d'un decoupage (flag = PACK_OP_SPLIT)
    stock_op_id = fields.Many2one('tcb.stock.picking.operation', string=u"Opération de stock")
    # Id du picking, toujours renseigné
    picking_id = fields.Many2one('stock.picking', string=u"Transfert")
    # code bare du produit, toujours renseigné sauf pour le flag 'PACK_OP_PASS'
    product_code = fields.Char(u"Code produit")
    # code barre de l'emplacement, toujours renseigné sauf pour le flag 'PACK_OP_PASS'
    location_code = fields.Char(u"Code emplacement")
    # toujours renseigné, ou 0 si le flag est 'PACK_OP_PASS'
    qty = fields.Integer(u"Quantité")
    # toujours renseigné, START = 0 et END = max
    sequence = fields.Integer(u"Séquence")
    # date et heure de l'action
    timestamp = fields.Datetime(string=u"Date")
    # statut du traitement de l'objet par la synchronisation vers les pickings
    state = fields.Selection([
        ('draft', u"À traiter"),
        ('done', u"Traité")],
        string=u"Statut du traitement TCB", default='draft')
    # date à laquelle l'objet est passé à 'done'
    date_done = fields.Datetime(string=u"Date de validation TCB")
    deleted = fields.Boolean(string=u"Picking passé puis modifié")

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'done':
            vals['date_done'] = fields.Datetime.now()
        return super(TcbPushPackOp, self).write(vals)


class TcbPushcart(models.Model):
    _name = 'tcb.push.cart'
    _order = 'cart_id, sequence'

    # flag chaque ligne possede un flag
    # un picking wave possede forcement un le flag 'START' avec un numero de sequence a 0
    # ensuite le flag décris l'action réalisé par le pickeur
    # START_CART Debut du chariot
    # END_CART Fin du chariot
    # MOVING_WH L'application est en mode << déménagement >>
    # CLASSIC L'application est en mode << classic >>.
    # -- la sequence sera forcement la plus haute pour le flag 'END_CART'
    # -- la sequence sera forcement = 0 pour le flag 'START_CART'
    flag = fields.Selection([
        ('START_CART', u"Début de vague"),
        ('END_CART', u"Fin de vague"),
        ('MOVING_WH', u"Déménagement"),
        ('CLASSIC', u"Split"),
    ], string=u"Flag", readonly=True, required=True)

    user_id = fields.Many2one('res.users', string=u"Utilisateur", required=True)
    product_id = fields.Many2one('product.product', u"Article", readonly=True)
    stock_product_line_id = fields.Char(string=u"Stock product line", readonly=True)
    owner_id = fields.Many2one('res.partner', u'Propriétaire', domain=[('customer', '=', True)], readonly=True)

    # Généré par l'application. sert de clef de regroupement des lignes
    cart_id = fields.Char(u"Numéro unique du chariot", readonly=True, required=True)

    # Numero de sequence unique par ligne et par 'cart_id'
    sequence = fields.Integer(u"Numéro de séquence", readonly=True)

    # Quantité selectionné par l'utilisateur. Pour les start/end, la quantité est mise arbitrairement à 1.
    qty = fields.Integer(u"Quantié", readonly=True, required=True)

    # date et heure de l'action
    timestamp = fields.Datetime(string=u"Date", readonly=True)

    # statut du traitement de l'objet par la synchronisation vers les pickings
    state = fields.Selection([('draft', u"À traiter"), ('done', u"Traité")], string=u"Statut du traitement TCB",
                             default='draft', readonly=True)
    warning_tcb = fields.Boolean(string=u"Warning TCB")
    last_tcb_status = fields.Char(string=u"Dernier statut TCB", readonly=True)
    date_last_tcb_status = fields.Datetime(string=u"Date du dernier statut TCB", readonly=True)

    # date à laquelle l'objet est passé à 'done'
    date_done = fields.Datetime(string=u"Date de validation TCB", readonly=True)

    @api.constrains('product_id', 'flag')
    def set_product_id_constraint(self):
        if self.flag not in ['START_CART', 'END_CART'] and not self.product_id:
            raise ValidationError(u"Veuillez remplir l'article")

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'done':
            vals['date_done'] = fields.Datetime.now()
        return super(TcbPushcart, self).write(vals)
