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
{
    'name': 'invoices factor',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'account',
    'depends': ['mail', 'account_voucher'],
    'description': """
send invoices and refunds to factors
====================================
# FACTOR SETTINGS

## Define factor banks

* go to "Sales > Configuration > Bank accounts"
* set factor settings

## Affect factor banks to your partners

Go to your partner profil in "accounting tab" and set the field" Factor bank account"

> **Now**
>
> * yout partners are factor compatible
> * factor banks are selectable in "accounting > bank and cash > Transmited factors > create"

# INVOICE SETTINGS

## Allow factor transmissions on invoices

* check the "allow factor transmission"
  * impossible if the partner's bank (of the invoice) is not factor compatible
  * automatic if the partner was already factor compatible

* click on the "send to factor" button at the top of the form.

# TRANSMIT INVOICES

* go to accounting > transmitted factors and select the factor bank you wish
* click on send to factor to mail it.

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/account_invoice.xml',
        'views/factor_transmission.xml',
        'views/res_partner_bank.xml',
        'views/res_partner.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
