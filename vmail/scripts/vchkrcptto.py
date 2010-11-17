#
# vmail/scripts/vchkrcptto.py
#
# Copyright (C) 2010 @UK Plc, http://www.uk-plc.net
#
# Author:
#   2010 Damien Churchill <damoxc@gmail.com>
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

from vmail.client import client, reactor
from vmail.scripts.base import DaemonScriptBase, argcount

class VChkRcptTo(DaemonScriptBase):

    def on_connect(self, result):
        return client.core.is_validrcptto(self.args[0]).addCallbacks(
            self.on_got_result,
            self.on_got_result_err
        )

    def on_got_result(self, (code, destination, rcpt_type)):
        return code

    def on_got_result_err(self, result):
        return 1

    @argcount(1)
    def run(self):
        if '@' not in self.args[0]:
            log.error('invalid argument')
            return 1

        return self.connect()
