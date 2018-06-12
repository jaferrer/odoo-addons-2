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

ATTACHMENT_FIELDS = ['name', 'type', 'datas', 'mimetype', 'res_model', 'res_field', 'res_id', 'res_name', 'description',
                     'index_content', 'company_id', 'protected_attachment']


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    protected_attachment = fields.Boolean(string=u"Protected Attachment", readonly=True)
    l10n_fr_hash = fields.Char(string="Inalteralbility Hash", readonly=True, copy=False)
    l10n_fr_secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True,
                                                    copy=False)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)

    @api.multi
    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on protected attachments when they are created"""
        self.ensure_one()
        # get the only one exact previous attachment in the securisation sequence
        prev_attachment = self.search([('protected_attachment', '=', True),
                                       ('company_id', '=', self.company_id.id),
                                       ('l10n_fr_secure_sequence_number', '!=', 0),
                                       ('l10n_fr_secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_attachment and len(prev_attachment) != 1:
            raise UserError(_(u"An error occured when computing the inalterability. "
                              u"Impossible to get the unique previous protected attachment."))

        # build and return the hash
        return self._compute_hash(prev_attachment.l10n_fr_hash if prev_attachment else '')

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

        for attachment in self:
            values = {}
            for field in ATTACHMENT_FIELDS:
                values[field] = _getattrstring(attachment, field)
            # make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            attachment.l10n_fr_string_to_hash = dumps(values, sort_keys=True, encoding="utf-8",
                                                      ensure_ascii=True, indent=None,
                                                      separators=(',', ':'))

    @api.model
    def create(self, vals):
        attachment = super(IrAttachment, self).create(vals)
        if attachment.protected_attachment and attachment.company_id._is_accounting_unalterable() and not \
                (attachment.l10n_fr_secure_sequence_number or attachment.l10n_fr_hash):
            new_number = attachment.company_id.l10n_fr_attachments_cert_sequence_id.next_by_id()
            vals_hashing = {'l10n_fr_secure_sequence_number': new_number,
                            'l10n_fr_hash': attachment._get_new_hash(new_number)}
            attachment.write(vals_hashing)
        return attachment

    @api.multi
    def write(self, vals):
        for attachment in self:
            if attachment.company_id._is_accounting_unalterable() and attachment.protected_attachment:
                for field in vals.keys():
                    if field in ATTACHMENT_FIELDS:
                        raise UserError(_(u"According to the French law, you cannot modify a protected attachment. "
                                          u"Forbidden fields: %s.") % field)
        return super(IrAttachment, self).write(vals)

    @api.multi
    def unlink(self):
        for attachment in self:
            if attachment.company_id._is_accounting_unalterable() and attachment.protected_attachment:
                raise UserError(_(u"Forbidden to delete a protected attachment."))
        return super(IrAttachment, self).unlink()

    @api.model
    def _check_hash_integrity(self, company_id):
        """Checks that all protected attachments have still the same data as when they were created
        and raises an error with the result.
        """

        attachments = self.search([('protected_attachment', '=', True),
                                   ('company_id', '=', company_id),
                                   ('l10n_fr_secure_sequence_number', '!=', 0)],
                                  order="l10n_fr_secure_sequence_number ASC")

        if not attachments:
            raise UserError(_(u"There is no attachment flagged for data inalterability yet for the company %s. "
                              u"This mechanism only runs for protected attachments generated after the installation of "
                              u"the module Attachments hash.") % self.env.user.company_id.name)
        previous_hash = ''
        for attachment in attachments:
            if attachment.l10n_fr_hash != attachment._compute_hash(previous_hash=previous_hash):
                raise UserError(_('Corrupted data on point of attachment with id %s.') % attachment.id)
            previous_hash = attachment.l10n_fr_hash

        attachments_sorted_date = attachments.sorted(lambda att: att.create_date)
        start_attachment = attachments_sorted_date[0]
        end_attachment = attachments_sorted_date[-1]

        report_dict = {'start_attachment_name': start_attachment.name,
                       'start_attachment_date': start_attachment.create_date,
                       'end_attachment_name': end_attachment.name,
                       'end_attachment_date': end_attachment.create_date}

        # Raise on success
        raise UserError(_('''Successful test !

                             The protected attachments are guaranteed to be in their original and inalterable state
                             From: %(start_attachment_date)s recorded on %(start_attachment_date)s
                             To: %(end_attachment_name)s recorded on %(end_attachment_date)s.'''
                          ) % report_dict)
