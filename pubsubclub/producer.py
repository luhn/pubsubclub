from __future__ import absolute_import

from twisted.python import log

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
        self.subscriptions = set()

    def onDeclaredVersions(self, *versions):
        """
        Once the consumer has declared the versions it supports, select the
        one we want to use.

        """
        version_set = {tuple(item) for item in versions}
        mutual_versions = version_set & self.SUPPORTED_VERSIONS
        if not mutual_versions:
            self.sendClose()
            return
        selected = sorted(mutual_versions)[0]
        self.send(102, list(selected))
        self.ready()

    def onSubscribe(self, topic):
        """
        Subscribe a consumer to a topic.

        """
        self.subscriptions.add(topic)

    def onUnsubscribe(self, topic):
        """
        Unsubscribe a consumer from a topic.

        """
        self.subscriptions.remove(topic)

    def publish(self, topic, message):
        """
        Check if subscribed to topic.  If we are, send message.

        """
        if not self.ready:
            return
        if topic in self.subscriptions:
            self.send(301, topic, message)


PASSTHROUGH = ['publish']
ProducerClient = make_client('ProducerClient', PASSTHROUGH, ProducerProtocol)
ProducerServer = make_server('ProducerServer', PASSTHROUGH, ProducerProtocol)
