# Copyright 2019 Eficent <http://www.eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade

_FIELD_RENAMES = [
    ('res.company', 'res_company', 'auto_currency_up',
     'currency_rates_autoupdate'),
]

XMLID_RENAMES = [
    ('currency_rate_update.currency_rate_update_service_multicompany_rule',
     'currency_rate_update.res_currency_rate_provider_multicompany'),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(env, _FIELD_RENAMES)
    openupgrade.rename_xmlids(env.cr, XMLID_RENAMES)
