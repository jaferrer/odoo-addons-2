import os
import time

import logging

import twain
from PyPDF2 import PdfFileMerger
from PyPDF2 import PdfFileReader

from OdooWrapper import _Scanner

PATH_TMP = '.'

_scanner = _Scanner()
scanners = _scanner.list_scanner()
print scanners

_scanner.set_scanner('TW-Brother ADS-2400N')

filenames = _scanner.scan(
    dpi=100,
    pixeltype='bw',
    bitdepth=8,
    duplex=True,
    quality=30
)
