# -*- coding: utf8 -*-
#
#    Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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
#    along with this
#
import hashlib
import logging
import re
import shutil
import os
import tempfile
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
from PIL import Image

from lxml import etree

from odoo import models, api, tools

_logger = logging.getLogger(__name__)
INSTALL_PATH = os.path.dirname(__file__)
INCH_TO_CM = 2.54


def get_options():
    """
    Parses the command-line options.
    """
    option = {
        'cut_start': "ODT-CUT-START",
        'cut_stop': "ODT-CUT-STOP",
        'top_header_level': 1,
        'img_width': "8cm",
        'img_height': "6cm",
        'img_dpi': 96,
        'with_network': True
    }
    return option


def log(msg, verbose=False):
    """
    Simple method to log if we're in verbose mode (with the :option:`-v`
    option).
    """
    if verbose:
        _logger.info(msg)


class Parser(models.AbstractModel):
    """
    porté de community v9 report_aeroo/extrafunctions.py pour les besoins de réanova
    """
    _inherit = 'report.report_aeroo.abstract'

    index_html = 0

    def complex_report(self, docids, data, report, ctx):
        ctx = dict(ctx) or {}
        ctx.update({
            'html_parse': self._xhtml_to_odt,
        })
        return super(Parser, self).complex_report(docids, data, report, ctx)

    def _xhtml_to_odt(self, xhtml):
        """
        Converts the XHTML content into ODT.

        :param xhtml: the XHTML content to import
        :type  xhtml: str
        :returns: the ODT XML from the conversion
        :rtype: str
        """
        self.index_html = self.index_html + 1
        xhtml = u'<?xml version="1.0"?>' \
                u'<html xmlns="http://www.w3.org/1999/xhtml"><head><title></title></head>' \
                u'<body>' + xhtml + u'</body></html>'
        xhtml = tools.ustr(xhtml.replace(u'<br>', u'<br/>'))
        self.options = get_options()
        xsl_dir = os.path.join(INSTALL_PATH, 'xsl')
        xslt_doc = etree.parse(os.path.join(xsl_dir, "xhtml2odt.xsl"))
        transform = etree.XSLT(xslt_doc)
        xhtml = self.handle_images(xhtml)
        xhtml = self.handle_links(xhtml)

        try:
            # must be valid xml at this point
            xhtml = etree.fromstring(
                xhtml)
        except etree.XMLSyntaxError as e:
            _logger.error(e)
            raise e
        params = {
            "url": "/",
            "heading_minus_level": str(self.options["top_header_level"] - 1),
        }
        if self.options["img_width"]:
            if hasattr(etree.XSLT, "strparam"):
                params["img_default_width"] = etree.XSLT.strparam(
                    self.options["img_width"])
            else:  # lxml < 2.2
                params["img_default_width"] = "'%s'" % self.options["img_width"]
        if self.options["img_height"]:
            if hasattr(etree.XSLT, "strparam"):
                params["img_default_height"] = etree.XSLT.strparam(
                    self.options["img_height"])
            else:  # lxml < 2.2
                params["img_default_height"] = "'%s'" % self.options["img_height"]
        odt = transform(xhtml, **params)
        # DEBUG
        stra = tools.ustr(odt).replace('<?xml version="1.0" encoding="utf-8"?>', '')
        stra = stra.replace('<?xml version="1.0"?>\n', '')
        return (u"<htmlparse>--key--" + tools.ustr(self.index_html) + u"--key--" + stra + u"</htmlparse>").\
            replace('\n', ' ')

    def handle_images(self, xhtml):
        """
        Handling of image tags in the XHTML. Local and remote images are
        handled differently: see the :meth:`handle_local_img` and
        :meth:`handle_remote_img` methods for details.

        :param xhtml: the XHTML content to import
        :type  xhtml: str
        :returns: XHTML with normalized ``img`` tags
        :rtype: str
        """
        # Handle local images
        # xhtml = re.sub('<img [^>]*src="([^"]+)"[^>]*>',
        #               self.handle_local_img, xhtml)
        # Handle remote images
        if self.options["with_network"]:
            xhtml = re.sub('<img [^>]*src="(https?://[^"]+)"[^>]*>',
                           self.handle_remote_img, xhtml)
        # print xhtml
        return xhtml

    def handle_remote_img(self, img_mo):
        """
        Downloads remote images to a temporary file and flags them for
        inclusion using the :meth:`handle_img` method.

        :param img_mo: the match object from the `re.sub` callback
        """
        src = img_mo.group(1)
        try:
            tmpfile = self.download_img(src)
        except (HTTPError, URLError):
            return img_mo.group()
        try:
            ret = self.handle_img(img_mo.group(), src, tmpfile)
        except IOError:
            return img_mo.group()

        os.remove(tmpfile)
        return ret

    @api.model
    def download_img(self, src):
        """
        Downloads the given image to a temporary location.

        :param src: the URL to download
        :type  src: str
        """

        # TODO: proxy support
        remoteimg = urlopen(src)
        tmpimg_fd, tmpfile = tempfile.mkstemp()
        tmpimg = os.fdopen(tmpimg_fd, 'w')
        tmpimg.write(remoteimg.read())
        tmpimg.close()
        remoteimg.close()
        return tmpfile

    def handle_img(self, full_tag, src, filename):
        """
        Imports an image into the ODT file.

        :param full_tag: the full ``img`` tag in the original XHTML document
        :type  full_tag: str
        :param src: the ``src`` attribute of the ``img`` tag
        :type  src: str
        :param filename: the path to the image file on the local disk
        :type  filename: str
        """

        if not os.path.exists(filename):
            _logger.error("%s does not exists", filename)
            raise IOError()
        # TODO: generate a filename (with tempfile.mkstemp) to avoid weird
        # filenames. Maybe use img.format for the extension
        if not os.path.exists(os.path.join(self.tmpdir, "Pictures")):
            os.mkdir(os.path.join(self.tmpdir, "Pictures"))
        newname = (hashlib.md5(filename).hexdigest() + os.path.splitext(filename)[1])
        shutil.copy(filename, os.path.join(self.tmpdir, "Pictures", newname))
        self._added_images.append(os.path.join("Pictures", newname))
        full_tag = full_tag.replace('src="%s"' % src,
                                    'src="Pictures/%s"' % newname)
        try:
            img = Image.open(filename)
        except IOError as io_error:
            _logger.error(io_error)
        else:
            width, height = img.size

            width_mo = re.search('width="([0-9]+)(?:px)?"', full_tag)
            height_mo = re.search('height="([0-9]+)(?:px)?"', full_tag)
            if width_mo and height_mo:
                width = float(width_mo.group(1)) / self.options["img_dpi"] \
                    * INCH_TO_CM
                height = float(height_mo.group(1)) / self.options["img_dpi"] \
                    * INCH_TO_CM
                full_tag = full_tag.replace(width_mo.group(), "")\
                                   .replace(height_mo.group(), "")
            elif width_mo and not height_mo:
                newwidth = float(width_mo.group(1)) / \
                    float(self.options["img_dpi"]) * INCH_TO_CM
                height = height * newwidth / width
                width = newwidth
                full_tag = full_tag.replace(width_mo.group(), "")
            elif not width_mo and height_mo:
                newheight = float(height_mo.group(1)) / \
                    float(self.options["img_dpi"]) * INCH_TO_CM
                width = width * newheight / height
                height = newheight
                full_tag = full_tag.replace(height_mo.group(), "")
            else:
                width = width / float(self.options["img_dpi"]) * INCH_TO_CM
                height = height / float(self.options["img_dpi"]) * INCH_TO_CM
            full_tag = full_tag.replace('<img',
                                        '<img width="%scm" height="%scm"' % (width, height))
        return full_tag

    @api.model
    def _add_styles(self, xml):
        xsl_dir = os.path.join(INSTALL_PATH, 'xsl')
        xslt_doc = etree.parse(os.path.join(xsl_dir, "styles.xsl"))
        transform = etree.XSLT(xslt_doc)
        contentxml = etree.fromstring(xml["content.xml"])
        stylesxml = etree.fromstring(xml["styles.xml"])

        xml["content.xml"] = str(transform(contentxml)).encode()
        xml["styles.xml"] = str(transform(stylesxml)).encode()

        return xml

    def handle_links(self, xhtml):
        """
        Turn relative links into absolute links using the :meth:`handle_links`
        method.
        """
        # Handle local images
        xhtml = re.sub('<a [^>]*href="([^"]+)"', self.handle_relative_links, xhtml)
        return xhtml

    @api.model
    def handle_relative_links(self, link_mo):
        """
        Do the actual conversion of links from relative to absolute. This
        method is used as a callback by the :meth:`handle_links` method.
        """
        return link_mo.group()
