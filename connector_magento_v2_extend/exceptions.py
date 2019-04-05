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


class BaseMagento2Error(Exception):
    def __init__(self, method, arguments):
        super(BaseMagento2Error, self).__init__()
        self.method = method
        self.arguments = arguments


class Magento2MaxRetryExceed(BaseMagento2Error):

    def __init__(self, method, arguments, max):
        super(Magento2MaxRetryExceed, self).__init__(method, arguments)
        self.max = max

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return u"Le nombre de de d'essai depassé; maximum=%s pour la requette %s avec les parametres %s" % (
            self.max, self.method, self.arguments
        )


class Magento2CallApiError(BaseMagento2Error):

    def __init__(self, method, arguments, status_code, reason):
        super(Magento2CallApiError, self).__init__(method, arguments)
        self.status_code = status_code
        self.reason = reason

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return u"Erreur lors de l'execution de la requete %s\nArgs: %s\n Status code:%s\nRaison:%s" % (
            self.method, self.arguments, self.status_code, self.reason
        )
