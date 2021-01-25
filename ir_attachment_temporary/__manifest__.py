# -*- coding: utf8 -*-
#
# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'ir attachment temporary',
    'summary': """
        Unlink temporary files
        """,
    'description': """
Base Report Async
=================
This modules unlink ir.attachment mark as temporary.
""",
    'version': '9.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical',
    'website': 'http://www.ndp-systemes.fr',
    'depends': ['base'],
    'data': [
        'data/config_parameter.xml',
        'data/cron.xml',
    ],
    'demo': [],
    'qweb': []
}
