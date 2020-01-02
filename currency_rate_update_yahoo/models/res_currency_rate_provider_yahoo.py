# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

from yahoofinancials import YahooFinancials

from odoo import models, fields, api, exceptions


class ResCurrencyRateProviderYahoo(models.Model):
    _inherit = 'res.currency.rate.provider'

    service = fields.Selection(
        selection_add=[('yahoo', "Yahoo")],
    )

    @api.multi
    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != 'yahoo':
            return super(ResCurrencyRateProviderYahoo, self)._get_supported_currencies()

        # List of currencies obrained from:
        # https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip
        return [
            "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
            "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
            "BSD", "BTN", "BWP", "BYR", "BZD", "CAD", "CDF", "CHF", "CLF", "CLP",
            "CNH", "CNY", "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP",
            "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS",
            "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF",
            "IDR", "IEP", "ILS", "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY",
            "KES", "KGS", "KHR", "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK",
            "LBP", "LKR", "LRD", "LSL", "LTL", "LVL", "LYD", "MAD", "MDL", "MGA",
            "MKD", "MMK", "MNT", "MOP", "MRO", "MUR", "MVR", "MWK", "MXN", "MXV",
            "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB",
            "PEN", "PGK", "PHP", "PKR", "PLN", "PYG", "QAR", "RON", "RSD", "RUB",
            "RWF", "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLL", "SOS",
            "SRD", "STD", "SVC", "SYP", "SZL", "THB", "TJS", "TMT", "TND", "TOP",
            "TRY", "TTD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VEF",
            "VND", "VUV", "WST", "XAF", "XAG", "XAU", "XCD", "XCP", "XDR", "XOF",
            "XPD", "XPF", "XPT", "YER", "ZAR", "ZMW", "ZWL"]

    @api.multi
    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()
        if self.service != 'yahoo':
            return super(ResCurrencyRateProviderYahoo, self)._obtain_rates(base_currency, currencies,
                                                                           date_from, date_to)
        min_date = min([date_from, date_to])
        max_date = max([date_from, date_to])
        if base_currency in currencies:
            currencies.remove(base_currency)
        res = {}
        for curr in currencies:
            search_name = base_currency + curr + '=X'
            yahoo_financials = YahooFinancials(search_name)

            yahoo_result = yahoo_financials.get_historical_price_data(fields.Date.to_string(date_from),
                                                                      fields.Date.to_string(date_to),
                                                                      'daily')
            contains_date_today = False
            if min_date <= fields.Date.today() and max_date >= fields.Date.today():
                date_today = fields.Date.to_string(fields.Date.today())
                contains_date_today = True
                # Download today currency
                if date_today not in res:
                    res[date_today] = {}
                rate = yahoo_financials.get_stock_price_data()[search_name]['regularMarketPreviousClose']
                if rate:
                    contains_date_today = True
                    res[date_today][curr] = rate
            if not contains_date_today:
                raise exceptions.UserError('Could not update the %s' % (curr))
            if yahoo_result.get('yahoo_result') and yahoo_result[search_name].get('prices'):
                list_prices = yahoo_result[search_name]['prices']
                for price_dict in list_prices:
                    date = price_dict['formatted_date']
                    if date not in res:
                        res[date] = {}
                    if curr not in res[date] and price_dict['close']:
                        res[date][curr] = price_dict['close']
        return res
