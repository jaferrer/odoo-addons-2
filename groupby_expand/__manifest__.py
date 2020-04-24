# -*- coding: utf-8 -*-

{
    'name': 'GroupBy Expand',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'website': 'https://ndp-systemes.fr',
    'category': 'Web',
    'description': 'Add a button to expand all groups',
    'depends': [
        'web',
    ],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/web_groups_expand.xml',
    ],
    'installable': True,
    'application': True
}
