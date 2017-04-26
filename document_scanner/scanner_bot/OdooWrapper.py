# -*- coding: utf8 -*-
#
# Copyright (C) 2016 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import requests
import random
import base64
import time
import os
import datetime
from pyScanLib import pyScanLib
from PyPDF2 import PdfFileMerger, PdfFileReader
import ConfigParser
import logging
# Import required for cx_freeze
from PIL import Image
from PIL import PngImagePlugin, ImagePalette, ImageFile, PdfImagePlugin
from PIL import BmpImagePlugin, GifImagePlugin, JpegImagePlugin
from PIL import PpmImagePlugin, TiffImagePlugin

PATH_BOT = os.environ['TMP'] + os.sep + 'scanner_bot'
PATH_LOG = PATH_BOT + os.sep + 'log'
PATH_TMP = PATH_BOT + os.sep + 'tmp'
PATH_CONFIG = os.environ['APPDATA'] + os.sep + 'scanner_bot' + os.sep + 'scanner.ini'
if not os.path.exists(os.environ['APPDATA'] + os.sep + 'scanner_bot'):
    os.makedirs(os.environ['APPDATA'] + os.sep + 'scanner_bot')

print "fichier temporaire du bot", PATH_BOT, PATH_TMP
print "fichier des log du bot", PATH_LOG
print "fichier de config du bot", PATH_CONFIG
if not os.path.exists(PATH_LOG):
    os.makedirs(PATH_LOG)
    logging.basicConfig(
        filename=PATH_LOG + os.sep + '/log_%s.log' % datetime.date.today().strftime('%Y%m%d'),
        level=logging.DEBUG,
        filemode='ab',
        datefmt='%d%m%Y')

if not os.path.exists(PATH_TMP):
    os.makedirs(PATH_TMP)

SECTION_CONFIG = 'config'
KEY_SCANNER_NAME = 'scanner.name'
KEY_SCANNER_CUSTOM_NAME = 'scanner.custom.name'
KEY_SERVER_URL = 'server.url'
PASSWORD = 'NBGEINLXGB4W6MLXKBZTK23RO52TQMZZMZZSC23MHFIUQMZDOVUDGOL2OI2DS6JUIJTXKNDPPAQSU4KM'


class _Error(object):
    def __init__(self):
        """
        :ivar self.error str
        :var result requests.Response
        """
        self.error = ''
        self.result = None

    def __repr__(self):
        return '<ResultRequest error[%s]: result request[%s]>' % (self.error, self.result and self.result.content or '')

    def json(self):
        if self.result and self.result.content.startswith('{"jsonrpc'):
            return self.result.json().get('result', [])
        else:
            return {}

    def handle_error(self):
        if self.ok():
            return False
        print u"Une erreur est apparut, message de l'erreur [%s]" % self.error
        print u"Voulez vous essayer de nouveau ou quitter le programme ?"
        print u"q = Quitter"
        print u"r = Réessayer"
        rq = raw_input(u"-->")
        if rq == 'r':
            print u"Relance de la requete précédente"
            return True
        elif rq == 'q':
            exit()

    def ok(self):
        return not self.error or self._res_contains_json() and not 'error' in self.result.json()

    def _res_contains_json(self):
        return bool(self.result) and self.result.content.startswith('{"jsonrpc')


class _OdooRequests(object):
    def __init__(self, url):
        self.last_poll = 0
        self.user = 'scanner_bot'
        self._session = requests.session()
        self.scanner = None
        self.url = url

    @staticmethod
    def test_url_odoo(url):
        res = True
        try:
            requests.get(url + '/web/login')
        except requests.RequestException:
            res = False
            logging.debug('url fausse %s' % url)
        return res

    def login(self):
        data_login = {
            'login': self.user,
            'password': base64.b32decode(PASSWORD),
            'redirect': '%s/web?' % self.url
        }
        res = _Error()
        try:
            res.result = self._session.post("%s/web/login" % self.url, data_login)
        except requests.RequestException as e:
            logging.error(e)
            res.error = e.message
        if res.error or res.result.content.startswith('{"jsonrpc') and res.result.json().get('error'):
            msg = res.error or u"Erreur lors de la connexion"
            logging.exception(requests.HTTPError(msg))
            if res.handle_error():
                self.login()
        else:
            print u"Connexion réussi au server %s comme utilisateur %s" % (self.url, self.user)
        self._load_session()
        self._check_modules()
        self.last_poll = self._get_last()

    def _load_session(self):
        r = self._call('/web/session/get_session_info')
        if r.handle_error():
            self.login()
        if r.ok():
            json = r.json()
            self.db = json['db']
            self.uid = json['uid']
            self.company_id = json['company_id']
            self.session_id = json['session_id']
            print u"Session chargée"

    def _call(self, url, data=None):
        """
        execute call method for odoo
        :param url:
        :param data:
        :rtype list:
        """
        if not data:
            data = {}
        req_id = random.randint(999, 999999)
        data_session_info = {"jsonrpc": "2.0", "method": "call", "params": data, "id": req_id}
        res = _Error()
        try:
            res.result = self._session.post(self.url + url, json=data_session_info)
        except requests.exceptions.RequestException as e:
            logging.exception(e)
            res.error = e.message
        if res.error or res.result.json().get('error'):
            if 'ir.attachment/create' in url:
                for args in data['args']:
                    args['datas'] = 'base64 pdf file too long too display'
            res.error = res.error or "%s for url=%s with data=%s" % (res.result.json()['error']['message'], url, data)
            logging.exception(requests.HTTPError(res.error))
        if res.result and res.result.json().get('id') != req_id:
            res = _Error()
        return res

    def _call_model(self, model, method, args=[], kwargs={}):
        data = {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        return self._call('/web/dataset/call_kw/%s/%s' % (model, method), data)

    def upload(self, doc, message):
        filename = "scan_%s_%s.pdf" % (message['user_id'], time.strftime("%H%M%S"))
        data = {
            'name': filename,
            'datas': base64.encodestring(doc.read()),
            'datas_fname': filename,
            'res_model': message['active_model'],
            'res_id': int(message['active_id'])
        }
        # model = 'ir.attachment'
        return self._call_model('ir.attachment', 'create', [data])

    def register_scanner(self, name):
        res = self._call_model('scanner.info', 'register', [name])
        if res.handle_error():
            self.register_scanner(name)

    def _get_last(self):
        return self._call_model("bus.bus", "get_last").json()[0]

    def increment_last_poll(self, results):
        self.last_poll = max([item['id'] for item in results.json()] or [self.last_poll])
        return self.last_poll

    def long_pollng(self):
        data = {
            "channels": (self.db, 'request.scanner'),
            "last": self.last_poll
        }
        return self._call('/longpolling/poll', data)

    def _check_modules(self):
        r = self._call('/web/session/modules')
        if r.handle_error():
            self.login()
        if r.ok():
            if 'document_scanner' not in r.json():
                print u"Le module <Document Scanner> n'est pas present sur le serveur"
                print u"Veuillez l'installer puis redémarer le programme"
                exit()
            else:
                print u"Module <Document Scanner> installé"


class _Config(object):
    def __init__(self):
        self._config = ConfigParser.RawConfigParser()
        self.scanner_name = ''
        self.scanner_manufacturer = ''
        self.scanner_custom_name = ''
        self.last_poll = 0
        self.file_exist = self._config.read(PATH_CONFIG)
        self.url = ''
        if self.file_exist:
            self.scanner_name = self._config.get(SECTION_CONFIG, KEY_SCANNER_NAME)
            self.scanner_custom_name = self._config.get(SECTION_CONFIG, KEY_SCANNER_CUSTOM_NAME)
            self.url = self._config.get(SECTION_CONFIG, KEY_SERVER_URL)

    def get_normalize_name(self):
        return self.scanner_custom_name.lower().replace(' ', '_')

    def write(self):
        if not self._config.has_section(SECTION_CONFIG):
            self._config.add_section(SECTION_CONFIG)
        self._config.set(SECTION_CONFIG, KEY_SCANNER_NAME, self.scanner_name)
        self._config.set(SECTION_CONFIG, KEY_SCANNER_CUSTOM_NAME, self.scanner_custom_name)
        self._config.set(SECTION_CONFIG, KEY_SERVER_URL, self.url)
        with open(PATH_CONFIG, 'wb') as configfile:
            self._config.write(configfile)


class IHM(object):
    def __init__(self):
        self._config = _Config()
        self._req = None
        self._scanner = _Scanner()

    def launch(self):
        print u"==========Démarage du Script============="
        self._init()
        self._loop()

    def _init(self):
        scanners = self._scanner.list_scanner()
        if self._config.file_exist:
            print u"Lecture du fichier de config scanner.ini"
            print u"Chargement du scanner %s alias %s" % (self._config.scanner_name, self._config.scanner_custom_name)
        else:
            print u"Fichier inexistant  ... Creation du fichier"
            print u"Etape de création de la configuration"
            print u"Etape 1/3"
            print u"Découverte des Scanners Disponnible..."
            print u"Nombre de scanners découvert %s" % len(scanners)
            for i in range(0, len(scanners)):
                print u"%s --> %s" % (i, scanners[i])
            if scanners:
                print u"Choisir le scanner voulu"
                choice = input(u"--> ")
                current_scanner = scanners[choice]
                self._scanner.set_scanner(current_scanner)
                self._config.scanner_name = current_scanner
                self._config.scanner_custom_name = self._choose_name()
                self._config.url = self._choose_url()
                print u"Enregistrement des informations"
                self._config.write()

        self._scanner.set_scanner(self._config.scanner_name)
        self._req = _OdooRequests(self._config.url)
        print u"Connexion à Odoo avec l'utilisateur %s" % self._req.user
        self._req.login()
        print u"Enregistrement du scanner"
        self._req.register_scanner(self._config.scanner_custom_name)
        print u"En attente de demande de scan"

    def _loop(self):
        while True:
            results = self._req.long_pollng()
            logging.debug(results)
            while not results.ok():
                logging.error(u"Reconnexion dans 30sec suite à une erreur")
                logging.error(results.error)
                print u"Reconnexion dans 30sec suite à une erreur"
                time.sleep(30)
                self._init()
                results = self._req.long_pollng()

            self._req.increment_last_poll(results)
            for message in [item['message']
                            for item in results.json()
                            if item.get('channel', ())
                            and 'request.scanner' == item['channel'][1]
                            and item['channel'][0] == self._req.db
                            and item['message'].get('scan_name') == self._config.get_normalize_name()
                            ]:
                print u"Scan en cours ..."
                pdf = self._scanner.scan()
                if pdf:
                    print u"Upload en cours ..."
                    res = self._req.upload(pdf, message)
                    if not res.ok():
                        print u"Une erreur est apparut lors de l'upload du fichier"
                    else:
                        print u"Upload Fini"
                else:
                    print u"Aucun document a uploader"
                print u"En attente de demande de scan"

    def _choose_name(self):
        print u"Nom du Scanner"
        name = raw_input(u"--> ")
        print u"Valider le nom (y/n): %s" % name
        yn = raw_input(u"--> ")
        if yn != 'y':
            return self._choose_name()
        else:
            return name

    def _choose_url(self):
        print u"Saisir l'adresse du serveur odoo"
        url = raw_input(u"-->").strip(" ")
        if _OdooRequests.test_url_odoo(url):
            return url
        else:
            print u"Mauvaise adresse"
            return self._choose_url()


class _Scanner(object):
    def __init__(self):
        self._psl = pyScanLib()
        self._scanner = ''

    def list_scanner(self):
        return self._psl.getScanners()

    def set_scanner(self, scanner):
        if not self._psl.scanner:
            self._psl.setScanner(scanner)
            self._scanner = scanner
        self._psl.setDPI(300)
        self._psl.setPixelType("color")

    def scan(self):
        self.set_scanner(self._scanner)
        filenames = []
        images = self._psl.scan_multi()
        self._psl.closeScanner()
        for i in range(0, len(images)):
            f = PATH_TMP + os.sep + "tmp_img_%s.pdf" % str(i)
            filenames.append(f)
            images[i].save(f)
        if filenames:
            final_file = PATH_TMP + os.sep + "document-output.pdf"
            if len(filenames) > 1:
                merger = PdfFileMerger()
                for filename in filenames:
                    merger.append(PdfFileReader(file(filename, 'rb')))
                merger.write(final_file)
                merger.close()
            else:
                final_file = filenames[0]
            return file(final_file, 'rb')
        return None

    def get_current_scanner(self):
        return self._psl.scanner
