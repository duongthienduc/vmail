#
# vmail/daemon/monitor.py
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

import os
import logging
import pyinotify

from twisted.internet import threads, task

from vmail.common import get_config, get_usage
from vmail.error import VmailException
from vmail.model import User, rw_db

log = logging.getLogger(__name__)

class MDSEventHandler(pyinotify.ProcessEvent):
    """
    This handler listends for changes to maildirsize files and then updates
    the database accordingly.
    """

    def process_default(self, event):
        if event.name != 'maildirsize':
            return

        # As this is an MDS file we want to scan it and update the user's
        # quota figures.
        username = os.path.basename(event.path)
        domain = os.path.basename(os.path.dirname(event.path))
        email = '%s@%s' % (username, domain)
        try:
            user = rw_db.query(User).filter_by(email=email).one()
        except:
            return

        try:
            user.usage = get_usage(domain, username)
        except:
            user.usage = 0
        rw_db.commit()

class Monitor(object):

    def __init__(self, mask=pyinotify.IN_DELETE | pyinotify.IN_CREATE |
            pyinotify.IN_MODIFY):
        self.mask = mask
        self.manager = pyinotify.WatchManager()
        self.handler = MDSEventHandler()
        self.notifier = pyinotify.Notifier(self.manager, self.handler)

    def get_maildirs(self):
        """
        Scan the mail store for all the maildirs to watch
        """
        log.debug('Scanning for maildirs')
        dirs = []
        mailstore = get_config('mailstore')
        for domain in os.listdir(mailstore):
            # hidden folder
            if domain[0] == '.':
                continue

            domain = os.path.join(mailstore, domain)
            for user in os.listdir(domain):
                dirs.append(os.path.join(domain, user))
        return dirs

    def start(self):
        """
        Start the maildir monitor running
        """
        log.info('Starting maildirsize monitor')
        threads.deferToThread(self._start).addCallback(self.on_started)

    def _start(self):
        dirs = self.get_maildirs()
        log.debug('Adding watches')
        self.watches = dict([(d, self.manager.add_watch(d, self.mask))
            for d in dirs])

    def on_started(self, result):
        log.debug('Starting processing')
        self.loop = task.LoopingCall(self.process_events)
        self.loop.start(0.1)

    def stop(self):
        self.loop.stop()
        self.notifier.stop()

    def process_events(self):
        self.notifier.process_events()
        if self.notifier.check_events(0.1):
            self.notifier.read_events()

    def add_watch(self, path):
        """
        Add a new directory to be monitored 
        """
        if path in self.watches:
            raise VmailException('Path already being monitored')
        self.watches[path] = self.manager.add_watch(path, self.mask)

    def remove_watch(self, path):
        """
        Remove a watch from the monitoring
        """
        if path not in self.watches:
            raise VmailException('Path not being monitored')
        self.manager.rm_watch(self.watches[path])
