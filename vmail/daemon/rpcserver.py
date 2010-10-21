#
# vmail/daemon/main.py
#
# Copyright (C) 2010 @UK Plc, http://www.uk-plc.net
#
# Author:
#   2010 Damien Churchill <damoxc@gmail.com>
#
# Based off rpcserver.py found in Deluge, written by Andrew Resch.
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
import sys
import stat
import fcntl
import logging
import datetime
import traceback

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, defer, threads
from twisted.python.failure import Failure

import vmail.common
from vmail.error import VmailError, RPCException, RPCError

log = logging.getLogger(__name__)
json = vmail.common.json

def export(func, *args, **kwargs):
    func._rpcserver_export = True
    doc = func.__doc__
    func.__doc__ = "**RPC Exported Function** \n\n"
    if doc:
        func.__doc__ += doc
    return func

def encode_object(obj):
    if isinstance(obj, datetime.datetime):
        tt = obj.timetuple()
        return dict([(k[3:], getattr(tt, k)) for k in dir(tt) if k[0:2] == 'tm'])
    if not isinstance(obj, object):
        raise TypeError(repr(obj) + " is not JSON serializable")
    __json__ = getattr(obj, '__json__', None)
    if not __json__:
        raise TypeError(repr(obj) + " is not JSON serializable")
    return __json__()

class VmailProtocol(Protocol):

    __buffer =  None

    def dataReceived(self, data):
        """
        Handle receiving requests from a vmail script or another source.

        :param data: The string representation of the method call
        :type data: string
        """
        try:
            request = json.loads(data)
        except Exception, e:
            log.info("Received invalid message (%r): %s", data, e)
            return

        log.debug('request: %r', request)

        if type(request) is not dict:
            log.info('Received invalid message: type is not dict')
            return

        if 'method' not in request or 'id' not in request:
            log.info('Received invalid request: missed method or id')
            return

        request_id = request['id']
        method = request['method']
        args = request.get('args', ())
        kwargs = request.get('kwargs', {})
        reactor.callLater(0, self._dispatch, request_id, method, args,
            kwargs)

    def sendData(self, data):
        self.transport.write(json.dumps(data, default=encode_object))

    def sendResponse(self, request_id, result):
        response = {
            'id': request_id,
            'result': result,
            'error': None
        }
        self.sendData(response)

    def _on_err_response(self, failure, request_id):
        """
        Sends an error response with the contents of the exception
        that was raised.
        """
        self.sendData({
            'id':     request_id,
            'result': None,
            'error': {
                'name': failure.type.__name__,
                'value': (failure.value.args[0] if failure.value.args else ''),
                'traceback': ''.join(traceback.format_tb(failure.tb))
            }
        })

    def _on_got_response(self, result, request_id):
        self.sendResponse(request_id, result)

    def _dispatch(self, request_id, method, args, kwargs):
        """
        This method is run when a RPC request is made. It will run the
        local method and will send either a RPC response or RPC error
        back to the client.
        """

        if method in self.factory.methods:
            meth = self.factory.methods[method]
            try:
                self._on_got_response(self._callMethod(meth, args, kwargs), request_id)
            except Exception:
                self._on_err_response(Failure(), request_id)
        else:
            error = VmailError('No method by that name')
            failure = Failure(error, VmailError)
            self._on_err_response(failure, request_id)

    def _callMethod(self, method, args, kwargs):
        """
        This method handles calling the method and any __before__
        or __after__ methods within a thread to ensure further connections
        aren't blocked.
        """
        if method.im_before:
            try:
                method.im_before(method)
            except Exception, e:
                log.error('running __before__() failed')
                log.exception(e)

        try:
            return method(*args, **kwargs)
        finally:
            if method.im_after:
                try:
                    method.im_after(method)
                except Exception, e:
                    log.error('running __after__() failed')
                    log.exception(e)

class VmailProtocolThreaded(VmailProtocol):
    """
    This is a subclass of the VmailProtocol that executes the RPC methods
    in their own thread to improve concurrency.
    """

    def _dispatch(self, request_id, method, args, kwargs):
        """
        This method is run when a RPC request is made. It will run the
        local method and will send either a RPC response or RPC error
        back to the client.
        """

        if method in self.factory.methods:
            meth = self.factory.methods[method]
            d = threads.deferToThread(self._callMethod, meth, args, kwargs)
            d.addCallback(self._on_got_response, request_id)
            d.addErrback(self._on_err_response, request_id)
        else:
            error = VmailError('No method by that name')
            failure = Failure(error, VmailError)
            self._on_err_response(failure, request_id)

class RpcMethod(object):
    """
    This class acts as a wrapper around methods that checks for before and
    after methods when its created to save having to do it for every
    RPC request.
    """

    def __init__(self, method):
        self.__method = method
        self.im_before = getattr(method.im_self, '__before__', None)
        self.im_after = getattr(method.im_self, '__after__', None)

    def __getattr__(self, key):
        return getattr(self.__method, key)

    def __call__(self, *args, **kwargs):
        try:
            return self.__method(*args, **kwargs)
        except RPCError:
            raise
        except Exception, e:
            log.exception(e)
            raise

class RpcServer(object):
    
    def __init__(self, socket_path=None, threaded=True):
        self.factory = Factory()
        if threaded:
            self.factory.protocol = VmailProtocolThreaded
        else:
            self.factory.protocol = VmailProtocol
        self.factory.methods = {}
        self.config = vmail.common.get_config()
        self.socket_path = socket_path
        self.port = None
        self.lockfile = None
        if self.socket_path:
            self.socket_path = os.path.abspath(self.socket_path)

    def register_object(self, obj, name=None):
        """
        Registers an object to export it's RPC methods. These methods should
        be exported with the export decorator prior to registering the
        object.

        :param obj: the object we want to export
        :type obj: object
        :param name: the name to use, if None, it will be the class name
        of the object
        :type name: str
        """
        if not name:
            name = obj.__class__.__name__.lower()

        for d in dir(obj):
            if d[0] == "_":
                continue
            if getattr(getattr(obj, d), '_rpcserver_export', False):
                log.debug("Registering method: %s.%s", name, d)
                self.factory.methods[name + "." + d] = RpcMethod(getattr(obj, d))

    def start(self):
        sock_path = self.socket_path or self.config['socket']
        if not os.path.isdir(os.path.dirname(sock_path)):
            log.fatal('Cannot create socket: directory missing')
            exit(1)

        # We want to check if another instance is running now
        self.lockfile = open(sock_path + '.sock', 'a+')
        try:
            fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as e:
            # We only care about other instances holding a lock
            if e.errno == 11:
                log.fatal('Another instance of vmaild is already running')
                exit(1)
            elif e.errno == 13:
                log.fatal('Permission denied checking lock file')
                exit(1)
            else:
                raise
        else:
            # Remove the socket file if it exists
            if os.path.exists(sock_path):
                os.remove(sock_path)

        self.port = reactor.listenUNIX(sock_path, self.factory)
        os.chmod(sock_path,
            stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO | stat.S_ISGID)
        
    def stop(self):
        d = None

        if self.port:
            d = self.port.stopListening()

        if self.lockfile:
            os.remove(self.lockfile.name)
            fcntl.flock(self.lockfile.fileno(), fcntl.LOCK_UN)

        return d
