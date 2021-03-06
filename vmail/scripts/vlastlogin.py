#
# vmail/scripts/vlastlogin.py
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

from vmail.client import client
from vmail.scripts.base import DaemonScriptBase, argcount

class VLastLogin(DaemonScriptBase):

    script = 'vlastlogin'
    usage  = 'Usage: %prog [options] user method [addr]'

    @argcount(2)
    def run(self):
        self.method = self.args[1].lower()
        if self.method not in ('imap', 'pop3', 'rcube', 'smtp'):
            self.log.error('incorrect method supplied')
            return 2

        self.connect()

        client.core.last_login(self.args[0], self.method,
            self.args[2] if len(self.args) == 3 else None).join()

        return 0
