# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Base Report Async',
    'summary': """
        Asynchronous report with job queue
        """,
    'version': '9.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Technical',
    'website': 'http://www.ndp-systemes.fr',
    'depends': [
        'web',
        'web_easy_download',
        'web_report_improved',
        'connector'
    ],
    'data': [
        'views/reports.xml',
        'data/config_parameter.xml',
        'data/cron.xml',
    ],
    'demo': [
    ],
    'qweb': []
}