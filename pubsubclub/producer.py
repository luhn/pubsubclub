from __future__ import absolute_import

from .base import ProtocolBase, make_client, make_server


class ProducerProtocol(ProtocolBase):
    """
    This can be either be
    :class:`autobahn.twisted.websocket.WebSocketClientProtocol` or
    :class:`autobahn.twisted.websocket.WebSocketServerProtocol`.

    """
    SUPPORTED_VERSIONS = [(1, 0)]

    def onConnect(self):
        print('Start handshake.')

    def onOpen(self):
        print('Start handshake.')

    def onDeclaredVersions(self, *versions):
        """
        Once the consumer has declared the versions it supports, select the
        one we want to use.

        """
        pass

    def onSubscribe(self, topic, message):
        """
        Subscribe a consumer to a topic.

        """
        pass

    def onUnsubscribe(self, topic, message):
        """
        Unsubscribe a consumer from a topic.

        """


class Producer(object):
    """
    def __init__(self, *args, **kwargs):
        super(Producer, self).__init__(*args, **kwargs)
    """

    def publish(self):
        """
        Distribute a pubsub to all subscribed consumers.

        """
        pass


ProducerClient = make_client('ProducerClient', Producer, ProducerProtocol)
ProducerServer = make_server('ProducerServer', Producer, ProducerProtocol)
