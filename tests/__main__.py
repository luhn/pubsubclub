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
    generate_id,
)


def test_basic():
    """
    Test a simple one-to-one connection with WAMP pubsub.

    """
    print('Running test_basic')
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


def test_connect_replay():
    """
    Test that when a producer connects, the consumer sends all existing
    subscription to it.

    """
    print('Running test_connect_replay')
    handshake = deferLater(reactor, 0.5, lambda: None)

    producer_connect = handshake
    publisher_dispatch = Deferred()

    # Events that should be triggered
    producer_pubsub_received = Deferred()
    client1_pubsub_received = Deferred()
    client2_pubsub_received = Deferred()

    class WampProducerServerProtocol(wamp.WampServerProtocol):
        def onSessionOpen(self):
            self.registerForPubSub('http://example.com/mytopic')
            publisher_dispatch.addCallback(
                lambda _: self.dispatch(
                    'http://example.com/mytopic', {'a': 'b'},
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

    class WampConsumerClient1Protocol(wamp.WampClientProtocol):
        def onSessionOpen(self):
            self.subscribe('http://example.com/mytopic', self.onEvent)
            self.subscribe('http://example.com/mytopic2', self.onEvent)

        def onEvent(self, topic, event):
            try:
                assert topic == 'http://example.com/mytopic'
                assert event == {'a': 'b'}
                client1_pubsub_received.callback(None)
            except:
                client1_pubsub_received.errback()

    class WampConsumerClient1Factory(wamp.WampClientFactory):
        protocol = WampConsumerClient1Protocol

    class WampConsumerClient2Protocol(wamp.WampClientProtocol):
        def onSessionOpen(self):
            self.subscribe('http://example.com/mytopic', self.onEvent)

        def onEvent(self, topic, event):
            try:
                assert topic == 'http://example.com/mytopic'
                assert event == {'a': 'b'}
                client2_pubsub_received.callback(None)
            except:
                client2_pubsub_received.errback()

    class WampConsumerClient2Factory(wamp.WampClientFactory):
        protocol = WampConsumerClient2Protocol

    consumer = ConsumerServer('localhost', 19100)
    WampConsumerServerFactory.consumer = consumer
    producer = ProducerClient([])
    WampProducerServerFactory.producer = producer
    producer_connect.addCallback(
        lambda _: producer.connect('localhost', 19100)
    )
    producer_connect.addCallback(
        lambda _: deferLater(reactor, 0.5, lambda: None),
    ).chainDeferred(publisher_dispatch)

    listenWS(WampProducerServerFactory('ws://localhost:19101'))
    connectWS(WampProducerClientFactory('ws://localhost:19101'))

    consumer_server = WampConsumerServerFactory('ws://localhost:19102')
    listenWS(consumer_server)
    consumer.processor = consumer_server
    connectWS(WampConsumerClient1Factory('ws://localhost:19102'))
    connectWS(WampConsumerClient2Factory('ws://localhost:19102'))

    return DeferredList([
        producer_pubsub_received,
        client1_pubsub_received,
        client2_pubsub_received,
    ])


def test_no_self_connect():
    """
    Test that when a producer connects, the consumer sends all existing
    subscription to it.

    """
    class WampConsumerServerFactory(ConsumerMixin, wamp.WampServerFactory):
        protocol = wamp.WampServerProtocol

    id = generate_id()
    consumer = ConsumerServer('localhost', 19200, id=id)
    consumer.processor = WampConsumerServerFactory('ws://localhost:19202')
    listenWS(consumer.processor)
    producer = ProducerClient(id=id)
    init_wait = deferLater(reactor, 0.5, producer.connect, 'localhost', 19200)

    def check_connection():
        """
        Make sure producer has no connections, because it's been controlled.

        """
        print(set(producer.nodes))
        assert set(producer.nodes) == set()

    return deferLater(reactor, 1.0, check_connection)


if __name__ == '__main__':
    import logging
    import sys
    logging.basicConfig(level=logging.INFO)

    d = test_basic()
    d.addCallback(lambda _: test_connect_replay())
    d.addCallback(lambda _: test_no_self_connect())
    exit_code = 0

    def errback(err):
        # On error, print and then exit with a 2
        reactor.stop()
        err.printTraceback()
        exit_code = 2

    d.addCallback(lambda _: reactor.stop())
    d.addErrback(errback)
    reactor.run()
    sys.exit(exit_code)
