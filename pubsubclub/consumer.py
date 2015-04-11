from __future__ import absolute_import

from .base import ProtocolBase, make_client, make_server


class ConsumerProtocol(ProtocolBase):
    """
    This can be either be
    :class:`autobahn.twisted.websocket.WebSocketClientProtocol` or
    :class:`autobahn.twisted.websocket.WebSocketServerProtocol`.

    """
    SUPPORTED_VERSIONS = [(1, 0)]

    def onConnect(self):
        print('Start handshake.')

    def onOpen(self):
        """
        Upon completing the WebSocket handshake, start the PubSubClub
        handshake.

        """
        print('Start handshake.')

    def onVersionChosen(self, version):
        """
        Once the publisher chooses the version, start sending over all the
        subscribers.

        """
        pass

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
        pass

    def unsubscribe(self, topic):
        """
        Unsubscribe ourselves from the topic.

        :param topic:  The topic from which to unsubscribe.
        :type topic:  str

        """
        pass


ConsumerClient = make_client('ConsumerClient', Consumer, ConsumerProtocol)
ConsumerServer = make_server('ConsumerServer', Consumer, ConsumerProtocol)
