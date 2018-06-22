# -*- coding: utf8 -*-
#
#    Copyright (C) 2018 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from hashlib import sha256
from json import dumps

from openerp import models, fields, api, _
from openerp.exceptions import UserError

SALE_CLOSING_FIELDS = ['name', 'company_id', 'date_closing_stop', 'date_closing_start', 'frequency', 'total_interval',
                       'cumulative_total', 'sequence_number', 'last_move_id', 'last_move_hash', 'currency_id']


class SaleClosingHash(models.Model):
    _inherit = 'account.sale.closing'

    l10n_fr_hash = fields.Char(string="Inalteralbility Hash", readonly=True, copy=False)
    l10n_fr_secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True,
                                                    copy=False)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)

    @api.multi
    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on sale closing lines when they are created"""
        self.ensure_one()
        # get the only one exact previous sale closing in the securisation sequence
        prev_sale_closing = self.search([('company_id', '=', self.company_id.id),
                                         ('l10n_fr_secure_sequence_number', '!=', 0),
                                         ('l10n_fr_secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_sale_closing and len(prev_sale_closing) != 1:
            raise UserError(_(u"An error occured when computing the inalterability. "
                              u"Impossible to get the unique previous sale closing line."))

        # build and return the hash
        return self._compute_hash(prev_sale_closing.l10n_fr_hash if prev_sale_closing else '')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256(previous_hash + self.l10n_fr_string_to_hash)
        return hash_string.hexdigest()

    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_str].type in ['many2many', 'one2many']:
                field_value = field_value.ids
            return str(field_value)

        for sale_closing in self:
            values = {}
            for field in SALE_CLOSING_FIELDS:
                values[field] = _getattrstring(sale_closing, field)
                # make the json serialization canonical
                #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
                sale_closing.l10n_fr_string_to_hash = dumps(values, sort_keys=True, encoding="utf-8",
                                                            ensure_ascii=True, indent=None,
                                                            separators=(',', ':'))

    @api.model
    def create(self, vals):
        sale_closing = super(SaleClosingHash, self).create(vals)
        if sale_closing.company_id._is_accounting_unalterable() and not \
                (sale_closing.l10n_fr_secure_sequence_number or sale_closing.l10n_fr_hash):
            new_number = sale_closing.company_id.l10n_fr_sale_closing_sequence_id.next_by_id()
            self.env.cr.execute("""UPDATE account_sale_closing
SET l10n_fr_secure_sequence_number = %s, l10n_fr_hash = %s
WHERE id = %s""", (new_number, sale_closing._get_new_hash(new_number), sale_closing.id))
            self.env.invalidate_all()
        return sale_closing

    @api.multi
    def write(self, vals):
        for sale_closing in self:
            if sale_closing.company_id._is_accounting_unalterable():
                for field in vals.keys():
                    if field in SALE_CLOSING_FIELDS:
                        raise UserError(_(u"According to the French law, you cannot modify a sale closing line. "
                                          u"Forbidden fields: %s.") % field)
        return super(SaleClosingHash, self).write(vals)

    @api.multi
    def unlink(self):
        for sale_closing in self:
            if sale_closing.company_id._is_accounting_unalterable():
                raise UserError(_(u"Forbidden to delete a sale closing line."))
        return super(SaleClosingHash, self).unlink()

    @api.model
    def _check_hash_integrity(self, company_id):
        """Checks that all protected sale closing lines have still the same data as when they were created
        and raises an error with the result.
        """
        sale_closings = self.search([('company_id', '=', company_id),
                                     ('l10n_fr_secure_sequence_number', '!=', 0)],
                                    order="l10n_fr_secure_sequence_number ASC")
        if not sale_closings:
            raise UserError(_(u"There is no sale closing line flagged for data inalterability yet for the company %s. "
                              u"This mechanism only runs for ale closing lines generated after the installation of "
                              u"the module Sale Closing hash.") % self.env.user.company_id.name)
        previous_hash = ''
        for sale_closing in sale_closings:
            if sale_closing.l10n_fr_hash != sale_closing._compute_hash(previous_hash=previous_hash):
                raise UserError(_(u"Corrupted data on point of sale order line closing with id %s.") % sale_closing.id)
            previous_hash = sale_closing.l10n_fr_hash

        sale_closings_sorted_date = sale_closings.sorted(lambda att: att.create_date)
        start_sale_closing = sale_closings_sorted_date[0]
        end_sale_closing = sale_closings_sorted_date[-1]

        report_dict = {'start_sale_closing_name': start_sale_closing.name,
                       'start_sale_closing_date': start_sale_closing.create_date,
                       'end_sale_closing_name': end_sale_closing.name,
                       'end_sale_closing_date': end_sale_closing.create_date}

        # Raise on success
        raise UserError(_('''Successful test !

                             The protected sale closing lines are guaranteed to be in their original and inalterable state
                             From: %(start_sale_closing_date)s recorded on %(start_sale_closing_date)s
                             To: %(end_sale_closing_name)s recorded on %(end_sale_closing_date)s.'''
                          ) % report_dict)
