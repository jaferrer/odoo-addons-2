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

import logging
import sys

from psycopg2 import OperationalError

from openerp.addons.connector.controllers.main import RunJobController
from openerp.addons.connector.queue.job import ENQUEUED
from openerp.addons.connector.exception import FailedJobError

_logger = logging.getLogger(__name__)


class RunJobControllerExtend(RunJobController):

    def __init__(self):
        def _try_perform_job_custom(self, session_hdl, job):
            if job.state != ENQUEUED:
                _logger.warning('job %s is in state %s '
                                'instead of enqueued in /runjob',
                                job.uuid, job.state)
                return

            with session_hdl.session() as session:
                job.set_started()
                self.job_storage_class(session).store(job)

            _logger.debug('%s started', job)
            with session_hdl.session() as session:
                job.perform(session)
                job.set_done()
                retry = job.retry
                try:
                    self.job_storage_class(session).store(job)
                except OperationalError as err:
                    if retry >= job.max_retries:
                        type_, value, traceback = sys.exc_info()
                        new_exc = FailedJobError("Max. retries (%d) reached: %s" %
                                                 (job.max_retries, value or type_)
                                                 )
                        raise new_exc.__class__, new_exc, traceback
                    raise err
            _logger.debug('%s done', job)

        if not hasattr(RunJobController, "connector_fix_retry_monkey_done"):
            RunJobController._try_perform_job = _try_perform_job_custom
            RunJobController.connector_fix_retry_monkey_done = True
        super(RunJobControllerExtend, self).__init__()
