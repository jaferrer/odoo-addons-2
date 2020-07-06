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
        from odoo.addons.console_progress_bar.console_progress_bar import ConsoleProgressBar

        progress = ConsoleProgressBar("TASK BEING EXECUTED DESC", len(recordset))
        for rec in recordset:
            progress.step_up()
    """
    def __init__(self, description, iterable_len, chunk_size=1):
        super(ConsoleProgressBar, self).__init__()
        self.cpt = 0
        self.chunk_size = chunk_size
        self.chunk_count = 1
        if iterable_len:
            self.chunk_count = iterable_len // chunk_size + (iterable_len % chunk_size and 1 or 0)
        _logger.info(description)
        self._show_progress()
        if not iterable_len:
            self.step_up()

    def __str__(self):
        return "(%d/%d)" % (self.cpt, self.chunk_count)

    def _show_progress(self, desc=""):
        """ displays one line progress bar into the console """
        pb_pos = int(math.ceil(100.0 / self.chunk_count * self.cpt))
        sys.stdout.write('\r')
        line = "[%-100s] %s" % ('=' * pb_pos, str(self))
        if desc:
            line = "%s - %s" % (line, desc)
        sys.stdout.write(line)
        sys.stdout.flush()

    def step_up(self, console_step_info=""):
        """
        step up progress indicator
        :param console_step_info: additional information on current process step to display at the end of the line
        into console
        :return: True if stepped up false otherwise
        """
        self.cpt += 1
        self._show_progress(desc=console_step_info)
        if self.cpt >= self.chunk_count:
            _logger.info(" => end")  # stop writing on the same line 'LF'
            return False
        return True
