# coding: utf-8

{
    'name': 'M14 Base Theme Menu Bar',
    'version': '1.0',
    'author': 'NDP Systèmes',
    'website': 'http://ndp-systemes.fr',
    'category': 'Generic Modules',
    'description': """
Module Base Theme Menu Bar
==========================
Theme de la barre de menu NDP
    """,
    'depends': [
        'web',
    ],
    'data': [
        'views/assets.xml',
        'views/web.xml',
    ],
    'qweb': [
        'static/src/xml/navbar.xml',
    ],
    'images': ['static/description/logo.png'],
    'installable': True,
    'application': True,
}
