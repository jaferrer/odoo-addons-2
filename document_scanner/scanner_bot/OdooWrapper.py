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

import twain
from fpdf import FPDF
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


def log_print(msg, show=True):
    logging.debug(msg)
    if show:
        print msg


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
        log_print(u"Une erreur est apparut, message de l'erreur [%s]" % self.error)
        log_print(u"Voulez vous essayer de nouveau ou quitter le programme ?")
        log_print(u"q = Quitter")
        log_print(u"r = Réessayer")
        rq = raw_input(u"-->")
        if rq == 'r':
            log_print(u"Relance de la requete précédente")
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
            log_print(u"Connexion réussi au server %s comme utilisateur %s" % (self.url, self.user))
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
            log_print(u"Session chargée")

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
            log_print(e)
            res.error = e.message
        if res.error or res.result.json().get('error'):
            log_print(res)
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
                log_print(u"Le module <Document Scanner> n'est pas present sur le serveur")
                log_print(u"Veuillez l'installer puis redémarer le programme")
                exit()
            else:
                log_print(u"Module <Document Scanner> installé")


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
        log_print(u"==========Démarage du Script=============")
        self._init()
        self._loop()

    def _init(self):
        scanners = self._scanner.list_scanner()
        if self._config.file_exist:
            log_print(u"Lecture du fichier de config scanner.ini")
            log_print(
                u"Chargement du scanner %s alias %s" % (self._config.scanner_name, self._config.scanner_custom_name))
        else:
            log_print(u"Fichier inexistant  ... Creation du fichier")
            log_print(u"Etape de création de la configuration")
            log_print(u"Etape 1/3")
            log_print(u"Découverte des Scanners Disponnible...")
            log_print(u"Nombre de scanners découvert %s" % len(scanners))
            for i in range(0, len(scanners)):
                log_print(u"%s --> %s" % (i, scanners[i]))
            if scanners:
                log_print(u"Choisir le scanner voulu")
                choice = input(u"--> ")
                current_scanner = scanners[choice]
                self._scanner.set_scanner(current_scanner)
                self._config.scanner_name = current_scanner
                self._config.scanner_custom_name = self._choose_name()
                self._config.url = self._choose_url()
                log_print(u"Enregistrement des informations")
                self._config.write()

        if self._scanner.set_scanner(self._config.scanner_name):
            log_print(u"Connextion au scanner %s reussi" % self._config.scanner_name)
            self._req = _OdooRequests(self._config.url)
            log_print(u"Connexion à Odoo avec l'utilisateur %s" % self._req.user)
            self._req.login()
            log_print(u"Enregistrement du scanner")
            self._req.register_scanner(self._config.scanner_custom_name)
            log_print(u"En attente de demande de scan")
        else:
            log_print(u"Veuiller vous assurer que le scanner %s est bien branché" % self._config.scanner_name)
            log_print(u"Reconnexion dans 30sec")
            time.sleep(30)
            self._init()

    def _loop(self):
        while True:
            results = self._req.long_pollng()
            logging.debug(results)
            scanne_done = False
            while not results.ok():
                logging.error(results.error)
                log_print(u"Reconnexion dans 30sec suite à une erreur")
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
                logging.debug(message)
                log_print(u"Scan en cours ...")
                filenames = self._scanner.scan(
                    dpi=message.get('scan_dpi_info', 300),
                    pixeltype=message.get('scan_color_info', 'color'),
                    duplex=message.get('scan_duplex', False)
                )
                log_print(u"Fusion des pages")
                file = self._scanner.merge_file(filenames)
                if file:
                    with open(file, 'rb') as pdf:
                        log_print(u"Envoi à Odoo en cours ...")
                        res = self._req.upload(pdf, message)
                        if not res.ok():
                            log_print(u"Une erreur est apparut lors de l'upload du fichier")
                        else:
                            log_print(u"Upload Fini")
                            scanne_done = True

                else:
                    log_print(u"Aucun document a uploader")
            if scanne_done:
                log_print(u"En attente de demande de scan")

    def _choose_name(self):
        log_print(u"Nom du Scanner")
        name = raw_input(u"--> ")
        log_print(u"Valider le nom (y/n): %s" % name)
        yn = raw_input(u"--> ")
        if yn != 'y':
            return self._choose_name()
        else:
            return name

    def _choose_url(self):
        log_print(u"Saisir l'adresse du serveur odoo")
        url = raw_input(u"-->").strip(" ")
        if _OdooRequests.test_url_odoo(url):
            return url
        else:
            log_print(u"Mauvaise adresse")
            return self._choose_url()


class _Scanner(object):
    def __init__(self):
        self._psl = pyScanLib()
        self._scanner = ''

    def list_scanner(self):
        return self._psl.getScanners()

    def set_scanner(self, scanner):
        if not self._psl.scanner:
            try:
                self._psl.setScanner(scanner)
                self._scanner = scanner
                return True
            except twain.excDSOpenFailed:
                logging.error("Impossible de se connecter au scanner")
                return False
        return True

    def scan(self, dpi=300, pixeltype='color', duplex=False):
        log_print(u"Configuration du scanner : dpi=%s npixeltype=%s nduplex=%s" % (dpi, pixeltype, duplex), False)
        self.set_scanner(self._scanner)
        self._psl.setDPI(dpi)
        self._psl.setPixelType(pixeltype)
        self._psl.scanner.SetCapability(twain.CAP_DUPLEXENABLED, twain.TWTY_BOOL, duplex)
        images = self._psl.scan_multi()
        self._psl.closeScanner()

        jpgs = []
        for i in range(0, len(images)):
            if pixeltype == 'color':
                f = PATH_TMP + os.sep + "tmp_%s_scan.jpg" % str(i)
                jpgs.append(f)
                images[i].save(f, optimize=True, quality=15)
            else:
                f = PATH_TMP + os.sep + "tmp_%s_scan.png" % str(i)
                jpgs.append(f)
                images[i].save(f, optimize=True)
        filenames = []

        for jpg in jpgs:
            width, height = Image.open(jpg).size
            pdf = FPDF(unit="pt", format=[width, height])
            pdf.add_page()
            pdf.image(jpg, 0, 0)
            destination = os.path.splitext(jpg)[0] + ".pdf"
            filenames.append(destination)
            pdf.output(destination, "F")

        return filenames

    def merge_file(self, filenames):
        final_file = PATH_TMP + os.sep + "document-output.pdf"
        if filenames:
            log_print("fusion de %s fichiers dans le fichier %s" % (len(filenames), final_file), False)
            if len(filenames) > 1:
                merger = PdfFileMerger()
                for filename in filenames:
                    log_print("ajout du fichier temporaire %s" % filename, False)
                    merger.append(PdfFileReader(file(filename, 'rb')))
                merger.write(final_file)
                merger.close()
            else:
                final_file = filenames[0]
            log_print("creation du fichier final %s" % final_file, False)
        return final_file

    def get_current_scanner(self):
        return self._psl.scanner
