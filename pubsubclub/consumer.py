from __future__ import absolute_import

import sys
import logging
import random

from twisted.internet import reactor
from twisted.internet.task import deferLater

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
        logging.info('consumer:  Connected to producer')
        logging.info(
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
        logging.info('consumer:  Version %s chosen.', '{}.{}'.format(*version))
        self.ready()
        self.ping()

        # Start sending out all existing subscriptions
        for topic in self.factory.processor.subscriptions.iterkeys():
            self.send(201, topic)

    def onPublish(self, topic, message):
        """
        Receive a pubsub and dispatch it to the end users.

        """
        logging.info('here')
        try:
            self.factory.processor.dispatch(topic, message)
        except:
            import traceback
            traceback.print_exc()


class Consumer(object):
    def subscribe(self, topic):
        """
        Subscribe to a topic if we haven't already subscribed.

        :param topic:  The topic to which to subscribe.
        :type topic:  str

        """
        logging.info('consumer:  Subscribing to %s (PCS201)', topic)
        for node in self.ready_nodes:
            node.send(201, topic)

    def unsubscribe(self, topic):
        """
        Unsubscribe ourselves from the topic.

        :param topic:  The topic from which to unsubscribe.
        :type topic:  str

        """
        logging.info('consumer:  Unsubscriber from %s (PCS202)', topic)
        for node in self.ready_nodes:
            node.send(202, topic)


ConsumerClient = make_client('ConsumerClient', Consumer, ConsumerProtocol)
ConsumerServer = make_server('ConsumerServer', Consumer, ConsumerProtocol)
