#
# vmail/model/classes.py
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

import hashlib

from sqlalchemy import and_, join, desc, text, exists, select
from sqlalchemy.orm import mapper, backref, relation

from vmail.common import get_mail_dir
from vmail.model.tables import *

class Blacklist(object):
    pass

class Package(object):

    def __json__(self):
        return {
            'id': self.id,
            'name': self.name,
            'quota': self.quota,
            'account_limit': self.account_limit
        }

class Domain(object):

    @staticmethod
    def create(domain, package, password):
        """
        Provides an easy way to initially setup a domain in
        the database.

        :param domain: The domain name to create mail hosting for
        :type domain: str
        :param package: The package to use for the domain
        :type package: Package
        :param password: The password to use for postmaster
        :type password: str
        """
        # Create the domain
        d = Domain()
        d.domain = domain.lower()
        d.package = package
        d._package = package.name
        d.quota = package.quota
        d.account_limit = package.account_limit

        # Create the postmaster user
        u = User()
        u.email = 'postmaster@' + d.domain
        u.name = 'Postmaster'
        u.password = password
        u.quota = package.quota
        u.admin = True
        u.enabled = True

        # Add the postmaster user to the domain
        d.users.append(u)

        return d

    @staticmethod
    def exists(domain):
        return select([mysql_sucks.c.test],
            exists(['NULL']
                ).where(Domain.domain==domain))

    def __json__(self):
        return {
            'id': self.id,
            'login_id': self.login_id,
            'domain': self.domain,
            'package': self._package,
            'package_id': self.package_id,
            'quota': self.quota,
            'account_limit': self.account_limit,
            'enabled': self.enabled
        }

class Forward(object):

    @staticmethod
    def exists(source):
        return select([mysql_sucks.c.test],
            exists(['NULL']
                ).where(Forward.source==source))

    def __json__(self):
        return {
            'source':      self.source,
            'destination': self.destination
        }

class Forwards(object):

    @staticmethod
    def exists(source):
        return select([mysql_sucks.c.test],
            exists(['NULL']
                ).where(Forwards.source==source))

    def __json__(self):
        return {
            'id':          self.id,
            'domain_id':   self.domain_id,
            'source':      self.source,
            'destination': self.destination
        }

class Host(object):

    def __json__(self):
        return {
            'ip_address': self.ip_address,
            'action': self.action,
            'comment': self.comment
        }

class Login(object):

    def __json__(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'method': self.method,
            'local_addr': self.local_addr,
            'remote_addr': self.remote_addr,
            'date': self.date
        }

class LoginDomain(object):
    pass

class LoginHourly(object):
    pass

class QpsmtpdConnection(object):
    pass

class QpsmtpdLog(object):
    pass

class QpsmtpdTransaction(object):
    pass

class QpsmtpdRecipient(object):
    pass

class ResolvedForward(object):

    def __init__(self, source=None, destination=None):
        self.source = source
        self.destination = destination

    def __json__(self):
        return {
            'source': self.source,
            'destination': self.destination
        }

class Transport(object):
    pass

class User(object):

    @property
    def maildir(self):
        (user, domain) = self.email.split('@')
        return get_mail_dir(domain, user)

    def __get_password(self):
        return self._cleartext

    def __set_password(self, password):
        self._cleartext = password
        self._password = hashlib.md5(password).hexdigest()

    password = property(__get_password, __set_password)

    @staticmethod
    def exists(email):
        return select([mysql_sucks.c.test],
            exists(['NULL']
                ).where(User.email==email))

    def __json__(self):
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'email': self.email,
            'secondary_email': self.secondary_email,
            'name': self.name,
            'password': self.password,
            'quota': self.quota,
            'usage': self.usage.bytes if self.usage else 0,
            'enabled': self.enabled,
            'admin': self.admin
        }

class UserQuota(object):

    def __json__(self):
        return {
            'id': self.id,
            'email': self.email,
            'bytes': self.bytes,
            'messages': self.messages
        }

class Vacation(object):

    def __json__(self):
        return {
            'id': self.id,
            'email': self.email,
            'subject': self.subject,
            'body': self.body,
            'cache': self.cache,
            'domain': self.domain,
            'created': self.created,
            'active': self.active
        }

class VacationNotification(object):
    pass

class Whitelist(object):

    def __json__(self):
        return {
            'address': self.address
        }

mapper(Blacklist, blacklist)

mapper(Package, packages)

mapper(Domain, domains, properties = {
    'package':     relation(Package, backref='domains'),
    '_package':    domains.c.package,
    'transports':  relation(Transport, backref=backref('domain')),
    'forwards':    relation(Forward, order_by=forwards.c.source),
    'forwardings': relation(Forwards, order_by=forwardings.c.source),
    'users':       relation(User, order_by=users.c.email,
                            backref=backref('domain', uselist=False))
})

mapper(Forward, forwards, properties = {
    'domain': relation(Domain)
})

mapper(Forwards, forwardings)

mapper(Host, hosts)

mapper(Login, logins)

mapper(LoginDomain, logins_domains)

mapper(LoginHourly, logins_hourly)

mapper(QpsmtpdConnection, qpsmtpd_connections)

mapper(QpsmtpdLog, qpsmtpd_log, properties = {
    'connection': relation(QpsmtpdConnection, backref='log')
})

mapper(QpsmtpdTransaction, qpsmtpd_transactions, properties = {
    'connection': relation(QpsmtpdConnection, backref='transactions'),
    'log': relation(QpsmtpdLog)
})

mapper(QpsmtpdRecipient, qpsmtpd_rcpts, properties = {
    'transaction': relation(QpsmtpdTransaction, backref='recipients'),
    '_transaction': qpsmtpd_rcpts.c.transaction
})

mapper(ResolvedForward, resolved_forwards)

mapper(Transport, transport)

mapper(User, users, properties = {
    'logins':     relation(Login, backref=backref('user', uselist=False)),
    'usage':      relation(UserQuota, lazy=False, uselist=False,
                    cascade='all'),
    'vacation':   relation(Vacation, uselist=False, cascade='all'),
    '_password':  users.c.password,
    '_cleartext': users.c.cleartext
})

mapper(UserQuota, user_quotas)
mapper(Vacation, vacation, properties = {
    'notifications': relation(VacationNotification, cascade='all')
})
mapper(VacationNotification, vacation_notification)

mapper(Whitelist, whitelist)
