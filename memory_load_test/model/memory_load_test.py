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
# 
import sys, logging
from openerp import api, fields, models
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession

_logger = logging.getLogger(__name__)


@job(default_channel='root')
def job_run_memory_test(session, model, uom, total_memory_to_reach, increase_step_memory):
    session.env[model].test_load(uom, total_memory_to_reach, increase_step_memory)

class MemoryLoadTest(models.TransientModel):
    _name = 'memory.load.test'

    total_memory_to_reach = fields.Float(string=u"Total to memory to reach", default=10)
    increase_step_memory = fields.Float(string=u"Increase step of memory", default=0.1)
    uom = fields.Selection([
        (1000, "Ko"),
        (100000, "Mo"),
        (1000000000, "Go")
    ], string=u"Unit of mesure", default=100000)
    use_job = fields.Boolean(string=u"Use job")

    @api.multi
    def run(self):
        self.ensure_one()
        if self.use_job:
            job_run_memory_test.delay(ConnectorSession.from_env(self.env), self._name, self.uom,
                                      self.total_memory_to_reach, self.increase_step_memory)
        else:
            self.test_load(self.uom, self.total_memory_to_reach, self.increase_step_memory)

    @api.model
    def test_load(self, uom, total_memory_to_reach, increase_step_memory):
        mem_step = self.set_mem_step(uom, increase_step_memory)
        mem_use = mem_step
        size_memory_use = sys.getsizeof(mem_use) / uom
        while size_memory_use < total_memory_to_reach:
            mem_use += mem_step
            size_memory_use = sys.getsizeof(mem_use) / uom
            _logger.info(u"###################### Memory load test : use %s / %s" % (size_memory_use,
                                                                                     total_memory_to_reach))
        del mem_step
        del mem_use

    @api.model
    def set_mem_step(self, uom, increase_step_memory):
        if uom == 1000000000:
            default_increase_memory = "a" * 100 * (2 ** 20)
        elif uom == 100000:
            default_increase_memory = "a" * 10 * (2 ** 10)
        else:
            default_increase_memory = "a" * 10 * (2 ** 3)
        increase_memory = default_increase_memory
        mem_step_size = sys.getsizeof(increase_memory) / uom
        while mem_step_size < increase_step_memory:
            increase_memory += default_increase_memory
            mem_step_size = sys.getsizeof(increase_memory) * 1.00 / uom
        return increase_memory
