import logging
import json

from twisted.internet.defer import Deferred
from twisted.internet.task import deferLater
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.web.server import NOT_DONE_YET

from pubsubclub.consul import ConsulDiscovery


nodes = [
    ('test1', '192.168.1.1', 123),
    ('test2', '192.168.1.2', 124),
    ('test3', '192.168.1.3', 125),
]
node_change = Deferred()
change_index = 0


def change_nodes(new_nodes):
    global nodes, change_index, node_change
    logging.info('Settings nodes to %s', repr(new_nodes))
    nodes = new_nodes
    change_index += 1
    node_change.callback(None)
    node_change = Deferred()


class ConsulMock(resource.Resource):
    """
    A simple HTTP server to mock the Consul agent.

    """
    isLeaf = True

    def render_GET(self, request):
        logging.info('ConsulMock:  Received request for %s', request.path)
        if request.path == '/v1/catalog/service/consul':
            self._services(request)
            return NOT_DONE_YET
        elif request.path == '/v1/agent/self':
            return self._self(request)

    def _services(self, request):
        def finish_request():
            logging.info('ConsulMock:  Sending new services.')
            response = json.dumps([{
                'Node': node,
                'Address': address,
                'ServiceID': 'pubsub',
                'ServiceName': 'pubsub',
                'ServiceTags': None,
                'ServiceAddress': '',
                'ServicePort': port,
            } for (node, address, port) in nodes])
            logging.info('ConsulMock:  Index is %i', change_index)
            request.setHeader('X-Consul-Index', str(change_index))
            logging.info('ConsulMock:  Content is:  %s', response)
            request.write(response)
            request.finish()

        if 'wait' in request.args:
            logging.info('ConsulMock:  Waiting for changes.')
            node_change.addCallback(lambda _: finish_request())
        else:
            logging.info('ConsulMock:  Not waiting for anything.')
            deferLater(reactor, 0.0001, finish_request)

    def _self(self, request):
        response = json.dumps({
            'Member': {
                'Name': 'test1',
                'Addr': '192.168.1.1',
                'Port': 123,
            },
        })
        logging.info('ConsulMock:  Responding with: %s', response)
        return response


class ClientMock(object):
    def __init__(self):
        self.connections = set()

    def connect(self, host, port):
        self.connections.add((host, port))

    def disconnect(self, host, port):
        self.connections.remove((host, port))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    client = ClientMock()
    site = server.Site(ConsulMock())
    reactor.listenTCP(18101, site)

    discovery = ConsulDiscovery('http://localhost:18101/', 'consul', client)
    discovery.start()

    def test_setup():
        compare = {
            ('192.168.1.2', 124),
            ('192.168.1.3', 125),
        }
        if client.connections != compare:
            raise AssertionError(
                '{!r} != {!r}'.format(client.connections, compare)
            )

    def test_change(self):
        """
        Test

        """
        change_nodes([
            ('test1', '192.168.1.1', 123),
            ('test3', '192.168.1.3', 125),
            ('test4', '192.168.1.4', 321),
        ])

        def assertions():
            compare = {
                ('192.168.1.3', 125),
                ('192.168.1.4', 321),
            }
            if client.connections != compare:
                raise AssertionError(
                    '{!r} != {!r}'.format(client.connections, compare)
                )

        return deferLater(reactor, 0.1, assertions)

    d = deferLater(reactor, 0.1, test_setup)
    d.addCallback(lambda _: deferLater(reactor, 0.5, lambda: None))
    d.addCallback(test_change)

    def errback(err):
        # On error, print and then exit with a 2
        reactor.stop()
        err.printTraceback()
        import sys
        sys.exit(2)

    d.addCallback(lambda _: reactor.stop())
    d.addErrback(errback)

    reactor.run()
