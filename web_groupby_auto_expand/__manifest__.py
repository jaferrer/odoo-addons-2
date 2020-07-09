# -*- coding: utf-8 -*-

{
    'name': 'Web GroupBy Auto Expand',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'website': 'https://ndp-systemes.fr',
    'category': 'Web',
    'description': """
web group by autoexpand
============================
add 'auto_expand_groupby': True in the ir.actions.act_window context to expand by default a groupby',
""",
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
