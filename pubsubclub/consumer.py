from __future__ import absolute_import

import logging

from .base import ProtocolBase, make_client, make_server


class ConsumerProtocol(ProtocolBase):
    """
    This can be either be
    :class:`autobahn.twisted.websocket.WebSocketClientProtocol` or
    :class:`autobahn.twisted.websocket.WebSocketServerProtocol`.

    """
    ROLE = 'consumer'
    SUPPORTED_VERSIONS = {(1, 0)}

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

    def onVersionChosen(self, version):
        """
        Once the publisher chooses the version, start sending over all the
        subscribers.

        """
        logging.info('consumer:  Version %s chosen.', '{}.{}'.format(*version))
        self.ready()

    def onPublish(self, topic, message):
        """
        Receive a pubsub and dispatch it to the end users.

        """
        pass


class Consumer(object):
    def subscribe(self, topic):
        """
        Subscribe to a topic if we haven't already subscribed.

        :param topic:  The topic to which to subscribe.
        :type topic:  str

        """
        logging.info('consumer:  Subscribing to %s', topic)

    def unsubscribe(self, topic):
        """
        Unsubscribe ourselves from the topic.

        :param topic:  The topic from which to unsubscribe.
        :type topic:  str

        """
        logging.info('consumer:  Unsubscriber from %s', topic)


ConsumerClient = make_client('ConsumerClient', Consumer, ConsumerProtocol)
ConsumerServer = make_server('ConsumerServer', Consumer, ConsumerProtocol)
