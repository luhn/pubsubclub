from __future__ import absolute_import

import sys
import random

from twisted.python import log
from twisted.internet import reactor
from twisted.internet.task import deferLater
from autobahn.wamp1 import protocol as wamp

from .base import ProtocolBase, make_client, make_server


class ConsumerProtocol(ProtocolBase):
    """
    This can be either be
    :class:`autobahn.twisted.websocket.WebSocketClientProtocol` or
    :class:`autobahn.twisted.websocket.WebSocketServerProtocol`.

    """
    ROLE = 'consumer'
    SUPPORTED_VERSIONS = {(1, 0)}
    pong_received = True

    def onOpen(self):
        """
        Upon completing the WebSocket handshake, start the PubSubClub
        handshake.

        """
        log.msg('consumer:  Connected to producer')
        log.msg(
            'consumer:  Declaring implemented versions: %s (PSC101)',
            ', '.join(
                '{}.{}'.format(*item) for item in self.SUPPORTED_VERSIONS
            ),
        )
        self.send(101, *[list(item) for item in self.SUPPORTED_VERSIONS])

    def ping(self):
        if self.pong_received is False:
            sys.stderr.write('Lost connection!\n')
            sys.stderr.flush()
            self.transport.loseConnection()
            return
        self.pong_received = False
        self.sendPing()
        deferLater(reactor, random.uniform(3.0, 7.0), self.ping)

    def onPong(self, _):
        self.pong_received = True

    def onVersionChosen(self, version):
        """
        Once the publisher chooses the version, start sending over all the
        subscribers.

        """
        log.msg('consumer:  Version %s chosen.', '{}.{}'.format(*version))
        self.ready()
        self.ping()

        # Start sending out all existing subscriptions
        for topic in self.factory.processor.subscriptions.iterkeys():
            self.send(201, topic)

    def onPublish(self, topic, message):
        """
        Receive a pubsub and dispatch it to the end users.

        """
        log.msg('here')
        try:
            # We're making the call to the classmethod to prevent an infinite
            # loop if if two producer/consumer servers are connected to
            # eachother.
            wamp.WampServerFactory.dispatch(
                self.factory.processor, topic, message,
            )
        except:
            import traceback
            traceback.print_exc()

    def subscribe(self, topic):
        """
        Subscribe to a topic from the producer.

        """
        if not self.ready:
            return
        self.send(201, topic)

    def unsubscribe(self, topic):
        """
        Unsubscribe from a topic from the producer.

        """
        if not self.ready:
            return
        self.send(202, topic)


PASSTHROUGH = ['subscribe', 'unsubscribe']
ConsumerClient = make_client('ConsumerClient', PASSTHROUGH, ConsumerProtocol)
ConsumerServer = make_server('ConsumerServer', PASSTHROUGH, ConsumerProtocol)
