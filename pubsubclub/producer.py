from __future__ import absolute_import

import logging

from .base import ProtocolBase, make_client, make_server


class ProducerProtocol(ProtocolBase):
    """
    This can be either be
    :class:`autobahn.twisted.websocket.WebSocketClientProtocol` or
    :class:`autobahn.twisted.websocket.WebSocketServerProtocol`.

    """
    ROLE = 'producer'
    SUPPORTED_VERSIONS = {(1, 0)}
    subscriptions = None

    def onOpen(self):
        logging.info('producer:  Connected to consumer')
        self.subscriptions = set()

    def onDeclaredVersions(self, *versions):
        """
        Once the consumer has declared the versions it supports, select the
        one we want to use.

        """
        logging.info(
            'producer:  Received implemented versions: %s',
            ', '.join(
                '{}.{}'.format(*item) for item in versions
            ),
        )
        version_set = {tuple(item) for item in versions}
        mutual_versions = version_set & self.SUPPORTED_VERSIONS
        if not mutual_versions:
            logging.error(
                'producer:  No mutually supported versions, aborting connection.'
            )
            self.sendClose()
            return
        logging.info(
            'producer:  Mutually supported versions:  %s',
            ', '.join(
                '{}.{}'.format(*item) for item in mutual_versions
            ),
        )
        selected = sorted(mutual_versions)[0]
        logging.info(
            'producer:  Selecting %s as version.',
            '{}.{}'.format(*selected),
        )
        self.send(102, list(selected))
        self.ready()

    def onSubscribe(self, topic):
        """
        Subscribe a consumer to a topic.

        """
        logging.info('producer:  Subscribing to %s', topic)
        self.subscriptions.add(topic)

    def onUnsubscribe(self, topic):
        """
        Unsubscribe a consumer from a topic.

        """
        logging.info('producer:  Unsubscribing to %s', topic)
        self.subscriptions.remove(topic)

    def publish(self, topic, message):
        """
        Check if subscribed to topic.  If we are, send message.

        """
        if topic in self.subscriptions:
            self.send(301, topic, message)


class Producer(object):
    """
    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)
    """

    def publish(self, topic, message):
        """
        Distribute a pubsub to all subscribed consumers.

        """
        for node in self.ready_nodes:
            node.publish(topic, message)


ProducerClient = make_client('ProducerClient', Producer, ProducerProtocol)
ProducerServer = make_server('ProducerServer', Producer, ProducerProtocol)
