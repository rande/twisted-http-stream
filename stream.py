# coding: utf-8
#
# Copyright 2009 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

__author__ = "Thomas Rabaix, Alexandre Fiori"
__version__ = "0.0.1"

"""Twisted client library to handle Http Streaming.

This code is an adaptation of https://github.com/fiorix/twisted-twitter-stream
"""

import base64, urllib
from twisted.protocols import basic
from twisted.internet import defer, protocol, ssl

from urlparse import urlparse

try:
    import simplejson as _json
except ImportError:
    try:
        import json as _json
    except ImportError:
        raise RuntimeError("A JSON parser is required, e.g., simplejson at "
                           "http://pypi.python.org/pypi/simplejson/")


class MessageReceiver(object):
    def connectionMade(self):
        pass

    def connectionFailed(self, why):
        pass

    def messageReceived(self, message):
        raise NotImplementedError

    def _registerProtocol(self, protocol):
        self._streamProtocol = protocol

    def disconnect(self):
        if hasattr(self, "_streamProtocol"):
            self._streamProtocol.factory.continueTrying = 0
            self._streamProtocol.transport.loseConnection()
        else:
            raise RuntimeError("not connected")


class HttpStreamProtocol(basic.LineReceiver):
    delimiter = "\r\n"

    def __init__(self):
        self.in_header = True
        self.header_data = []
        self.status_data = ""
        self.status_size = None

    def connectionMade(self):
        self.transport.write(self.factory.header)
        self.factory.consumer._registerProtocol(self)

    def lineReceived(self, line):
        while self.in_header:
            if line:
                self.header_data.append(line)
            else:
                http, status, message = self.header_data[0].split(" ", 2)
                status = int(status)
                if status == 200:
                    self.factory.consumer.connectionMade()
                else:
                    self.factory.continueTrying = 0
                    self.transport.loseConnection()
                    self.factory.consumer.connectionFailed(RuntimeError(status, message))

                self.in_header = False
            break
        else:
            try:
                self.status_size = int(line, 16)
                self.setRawMode()
            except:
                pass

    def rawDataReceived(self, data):
        if self.status_size is not None:
            data, extra = data[:self.status_size], data[self.status_size:]
            self.status_size -= len(data)
        else:
            extra = ""

        self.status_data += data
        if self.status_size == 0:
            try:
                # ignore newline keep-alive
                message = _json.loads(self.status_data)
            except:
                pass
            else:
                self.factory.consumer.messageReceived(message)
            self.status_data = ""
            self.status_size = None
            self.setLineMode(extra)


class HttpStreamFactory(protocol.ReconnectingClientFactory):
    maxDelay = 120
    protocol = HttpStreamProtocol

    def __init__(self, consumer):
        if isinstance(consumer, MessageReceiver):
            self.consumer = consumer
        else:
            raise TypeError("consumer should be an instance of twistedhttpstream.MessageReceiver")

    def make_header(self, username, password, method, url, postdata=""):
        auth = base64.encodestring("%s:%s" % (username, password)).strip()
        header = [
            "%s %s HTTP/1.1" % (method, url.path),
            "Authorization: Basic %s" % auth,
            "User-Agent: twisted http stream",
            "Host: %s" % url.netloc,
            "Accept: 'application/json",
        ]

        if method == "GET":
            self.header = "\r\n".join(header) + "\r\n\r\n"

        elif method == "POST":
            header += [
                "Content-Type: application/x-www-form-urlencoded",
                "Content-Length: %d" % len(postdata),
            ]
            self.header = "\r\n".join(header) + "\r\n\r\n" + postdata

def stream(reactor, url, consumer, username=None, password=None):
    url = urlparse(url)

    tw = HttpStreamFactory(consumer)
    tw.make_header(username, password, "GET", url)

    if url.scheme == "https":
        reactor.connectSSL(url.netloc, 443, tw, ssl.ClientContextFactory())
    else:
        reactor.connectTCP(url.netloc, 80, tw)

    
    