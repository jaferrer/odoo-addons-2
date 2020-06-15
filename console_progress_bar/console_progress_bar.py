# -*- coding: utf8 -*-
#
# Copyright (C) 2020 NDP Systèmes (<http://www.ndp-systemes.fr>).
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

import sys
import math
import logging

_logger = logging.getLogger(__name__)


class ConsoleProgressBar:
    """
    how to:
    . add 'ndp_tools' to module dependencies
    . usage:
    .   from odoo.addons.console_progress_bar.console_progress_bar import ConsoleProgressBar
    example 1:
    * console_progress_bar = ConsoleProgressBar("TASK BEING EXECUTED DESC", len(recordset))
    * for rec in recordset:
    *   console_progress_bar.next_val()
    example 2:
    * progress = ConsoleProgressBar("TASK BEING EXECUTED DESC", len(recordset), chunk_size=500)
    * chunk = progress.next_val(recordset)
    * while chunk:
    *   chunk. [..treatment..]
    *   chunk = progress.next_val(recordset)
    """
    def __init__(self, current_treatment_description, iterable_len, chunk_size=1):
        super(ConsoleProgressBar, self).__init__()
        self.cpt = 0
        self.chunk_size = chunk_size
        self.chunk_count = int(math.ceil((iterable_len or 1) / chunk_size))
        _logger.info(current_treatment_description)
        self._show_progress()
        if not iterable_len:
            self.next_val()

    def __str__(self):
        return "(%d/%d)" % (self.cpt, self.chunk_count)

    def _show_progress(self, desc=False):
        pb_pos = int(math.ceil(100.0 / self.chunk_count * self.cpt))
        sys.stdout.write('\r')
        line = "[%-100s] %s" % ('=' * pb_pos, str(self))
        if desc:
            line = "%s - %s" % (line, desc)
        sys.stdout.write(line)
        sys.stdout.flush()

    def next_val(self, iterable=None, desc=""):
        """
        step up progress indicator
        :param iterable: iterable used to find current treatment item or chunk
        :param desc: additional information on current process step to display at the end of the line
        :return: current treatment item or chunk
        """
        self.cpt += 1
        self._show_progress(desc=desc)
        if self.cpt >= self.chunk_count:
            _logger.info(" => OK")
            return False
        if not iterable:
            return True
        items_done = (self.cpt - 1) * self.chunk_size
        return iterable[items_done:items_done + self.chunk_size] if iterable else True
