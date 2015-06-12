from twisted.internet import reactor
from autobahn.wamp1 import protocol as wamp
from autobahn.twisted.websocket import listenWS

from pubsubclub import (
    ConsumerMixin, ProducerMixin, ConsumerServer, ProducerClient, consul,
)


class WampServerProtocol(wamp.WampServerProtocol):
    def onSessionOpen(self):
        print("Whoa")
        self.registerForRpc(self, "http://example.com/pubsub#")
        self.registerForPubSub('http://example.com/mytopic')
        self.registerForPubSub('http://example.com/mytopic2')
        self.registerForPubSub('http://example.com/mytopic3')

    @wamp.exportRpc('publish')
    def _publish(self, data):
        try:
            self.dispatch(
                data['channel'],
                data['content'],
                exclude=[self],
            )
        except:
            import traceback
            traceback.print_exc()
        return {}


class WampServerFactory(ConsumerMixin, ProducerMixin, wamp.WampServerFactory):
    protocol = WampServerProtocol


if __name__ == '__main__':
    # import logging
    # logging.basicConfig(level=logging.INFO)

    from twisted.python import log
    import sys
    log.startLogging(sys.stderr)

    consumer = ConsumerServer('0.0.0.0', 19000)
    WampServerFactory.consumer = consumer
    producer = ProducerClient([])
    WampServerFactory.producer = producer

    server = WampServerFactory('ws://localhost:9900')
    listenWS(server)
    consumer.processor = server

    discovery = consul.ConsulDiscovery(
        'http://localhost:8500/', 'pubsubclub', producer,
    )
    discovery.start()
    print('Starting...')

    reactor.run()
