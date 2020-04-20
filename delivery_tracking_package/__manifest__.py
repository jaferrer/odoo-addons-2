# Author: Guewen Baconnier
# Copyright 2015 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Delivery Tracking Package',
    'version': '0.1',
    'author': 'Camptocamp, Agile Business Group, '
              'Odoo Community Association (OCA)',
    'maintainer': 'Ndp Systemes',
    'license': 'AGPL-3',
    'category': 'Delivery',
    'depends': ['delivery_tracking'],
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'security/ir.model.access.csv',
        'security/package_preparation_security.xml',

        'views/views.xml',
        'views/inherit_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
