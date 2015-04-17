from __future__ import print_function


from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet.task import deferLater

from autobahn.twisted.websocket import listenWS, connectWS
from autobahn.wamp1 import protocol as wamp

from pubsubclub import (
    ConsumerMixin,
    ProducerMixin,
    ConsumerServer,
    ProducerClient,
)


def test_basic():
    """
    Test a simple one-to-one connection with WAMP pubsub.

    """
    # Awful (but simple) way of making sure handshake is complete
    handshake = deferLater(reactor, 0.5, lambda: None)
    # Ordering the things to do
    consumer_client_subscribe = handshake
    publisher_dispatch = Deferred()

    # All the events that should be triggered
    producer_pubsub_received = Deferred()
    consumer_pubsub_received = Deferred()

    class WampProducerServerProtocol(wamp.WampServerProtocol):
        def onSessionOpen(self):
            self.registerForPubSub('http://example.com/mytopic')
            publisher_dispatch.addCallback(
                lambda _: self.dispatch(
                    'http://example.com/mytopic', {'a': 'b'},
                )
            )
            # This one shouldn't go through
            publisher_dispatch.addCallback(
                lambda _: self.dispatch(
                    'http://example.com/NOTmytopic', {'a': 'b'},
                )
            )

    class WampProducerServerFactory(ProducerMixin, wamp.WampServerFactory):
        protocol = WampProducerServerProtocol

    class WampProducerClientProtocol(wamp.WampClientProtocol):
        def onSessionOpen(self):
            self.subscribe('http://example.com/mytopic', self.onEvent)

        def onEvent(self, topic, event):
            try:
                assert topic == 'http://example.com/mytopic'
                assert event == {'a': 'b'}
                producer_pubsub_received.callback(None)
            except:
                producer_pubsub_received.errback()

    class WampProducerClientFactory(wamp.WampClientFactory):
        protocol = WampProducerClientProtocol

    class WampConsumerServerProtocol(wamp.WampServerProtocol):
        def onSessionOpen(self):
            self.registerForPubSub('http://example.com/mytopic')

    class WampConsumerServerFactory(ConsumerMixin, wamp.WampServerFactory):
        protocol = WampConsumerServerProtocol

    class WampConsumerClientProtocol(wamp.WampClientProtocol):
        def onSessionOpen(self):
            consumer_client_subscribe.addCallback(
                lambda _: self.subscribe(
                    'http://example.com/mytopic', self.onEvent,
                )
            )
            consumer_client_subscribe.addCallback(
                lambda _: deferLater(reactor, 0.5, lambda: None)
            ).chainDeferred(publisher_dispatch)

        def onEvent(self, topic, event):
            try:
                assert topic == 'http://example.com/mytopic'
                assert event == {'a': 'b'}
                consumer_pubsub_received.callback(None)
            except:
                consumer_pubsub_received.errback()

    class WampConsumerClientFactory(wamp.WampClientFactory):
        protocol = WampConsumerClientProtocol

    consumer = ConsumerServer('localhost', 19000)
    WampConsumerServerFactory.consumer = consumer
    producer = ProducerClient([
        ('localhost', 19000),
    ])
    WampProducerServerFactory.producer = producer

    listenWS(WampProducerServerFactory('ws://localhost:19001'))
    connectWS(WampProducerClientFactory('ws://localhost:19001'))

    consumer_server = WampConsumerServerFactory('ws://localhost:19002')
    listenWS(consumer_server)
    consumer.processor = consumer_server
    connectWS(WampConsumerClientFactory('ws://localhost:19002'))

    return DeferredList([
        consumer_client_subscribe,
        publisher_dispatch,
        producer_pubsub_received,
        consumer_pubsub_received,
    ])


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.ERROR)

    d = test_basic()

    def errback(err):
        # On error, print and then exit with a 2
        reactor.stop()
        err.printTraceback()
        import sys
        sys.exit(2)

    d.addCallback(lambda _: reactor.stop())
    d.addErrback(errback)
    reactor.run()
