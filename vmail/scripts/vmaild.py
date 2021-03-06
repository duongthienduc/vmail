#
# vmail/scripts/vmaild.py
#
# Copyright (C) 2010-2012 @UK Plc, http://www.uk-plc.net
#
# Author:
#   2010-2012 Damien Churchill <damoxc@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.    If not, write to:
#   The Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor
#   Boston, MA    02110-1301, USA.
#

from gevent.monkey import patch_all; patch_all()

import os
import re

from vmail.scripts.base import ScriptBase
from vmail.common import get_config_dir
from vmail.daemon.daemon import Daemon

class VMailD(ScriptBase):

    log_config   = get_config_dir('logging.cfg')
    log_filename = '/var/log/vmail/vmaild.log'
    log_format   = 'full'

    def run(self):
        self.daemon = Daemon()
        try:
            return self.daemon.start()
        except KeyboardInterrupt:
            self.daemon.stop()
            return 0
        except Exception, e:
            self.log.exception(e)
            self.daemon.stop()
            return 1
