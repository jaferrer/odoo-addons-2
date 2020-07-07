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
from . import console_progress_bar


class Chunkify(console_progress_bar.ConsoleProgressBar):
    """
     how to:
     . add 'ndp_tools' to module dependencies
     . usage:
         from openerp.addons.ndp_tools.chunkify import Chunkify

         chunkify = Chunkify(recordset, chunk_size=500, description="TASK BEING EXECUTED DESC")
         chunk = chunkify.step_up()
         while chunk:
            job_do_something.delay(ConnectorSession.from_env(self.env), 'my.model', chunk.ids,
                                                     description=u"doing something on my model - chunk : %s" % progress)
         chunk = chunkify.step_up()
     """
    def __init__(self, iterable, chunk_size, description):
        assert iterable
        super(Chunkify, self).__init__(description, len(iterable), chunk_size)
        self.iterable = iterable

    def step_up(self, console_step_info=""):
        slice_left_idx = self.cpt * self.chunk_size
        slice_right_idx = slice_left_idx + self.chunk_size
        if self.cpt < self.chunk_count:
            super(Chunkify, self).step_up(console_step_info)
        return self.iterable[slice_left_idx:slice_right_idx]
