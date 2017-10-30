# -*- coding: utf8 -*-
#
# Copyright (C) 2017 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
    'name': 'Sale Order Report Aeroo',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Account',
    'depends': ['sale', 'report_aeroo'],
    'description': """
Sale Order Report Aeroo
============================
Replaces the basic report by a improved one.
to customize your the report you only need to inherit like this
<record id="sale_order_report_aeroo.sale_order_report_aeroo" model="ir.actions.report.xml">
    <field name="report_rml">yourmodule/your_report.odt</field>
</record>
""",
    'website': 'http://www.ndp-systemes.fr',
    'data': ['sale_order_report_aeroo.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
