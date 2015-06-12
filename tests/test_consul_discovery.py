import json

from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet.task import deferLater
from twisted.web import server, resource
from twisted.internet import reactor
from twisted.web.server import NOT_DONE_YET

from pubsubclub import consul


nodes = [
    ('test1', '192.168.1.1', 123),
    ('test2', '192.168.1.2', 124),
    ('test3', '192.168.1.3', 125),
]
node_change = Deferred()
change_index = 0


def change_nodes(new_nodes):
    global nodes, change_index, node_change
    log.msg('Settings nodes to %s', repr(new_nodes))
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
        log.msg('ConsulMock:  Received request for %s', request.path)
        if request.path == '/v1/health/service/consul':
            self._services(request)
            return NOT_DONE_YET
        elif request.path == '/v1/agent/self':
            return self._self(request)
        else:
            return 'FATAL'

    def _services(self, request):
        def finish_request():
            log.msg('ConsulMock:  Sending new services.')
            response = json.dumps([{
                'Node': {
                    'Node': node,
                    'Address': address,
                },
                'Service': {
                    'ID': 'pubsub',
                    'Service': 'pubsub',
                    'Tags': None,
                    'Port': port,
                },
                'Checks': [{
                    'Node': node,
                    'CheckID': 'service:pubsub',
                    'Name': 'Service \'pubsub\' check',
                    'Status': 'passing',
                    'Notes': '',
                    'Output': '',
                    'ServiceID': 'pubsub',
                    'ServiceName': 'pubsub',
                },],
            } for (node, address, port) in nodes])
            log.msg('ConsulMock:  Index is %i', change_index)
            request.setHeader('X-Consul-Index', str(change_index))
            log.msg('ConsulMock:  Content is:  %s', response)
            request.write(response)
            request.finish()

        if 'wait' in request.args:
            log.msg('ConsulMock:  Waiting for changes.')
            node_change.addCallback(lambda _: finish_request())
        else:
            log.msg('ConsulMock:  Not waiting for anything.')
            deferLater(reactor, 0.0001, finish_request)

    def _self(self, request):
        response = json.dumps({
            'Member': {
                'Name': 'test1',
                'Addr': '192.168.1.1',
                'Port': 123,
            },
        })
        log.msg('ConsulMock:  Responding with: %s', response)
        return response


class ClientMock(object):
    def __init__(self):
        self.connections = set()

    def connect(self, host, port):
        self.connections.add((host, port))

    def disconnect(self, host, port):
        self.connections.remove((host, port))


if __name__ == '__main__':
    import sys
    log.startLogging(sys.stdout)
    client = ClientMock()
    site = server.Site(ConsulMock())
    reactor.listenTCP(18101, site)

    discovery = consul.ConsulDiscovery(
        'http://localhost:18101/', 'consul', client,
    )
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
        Test chn

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

        return deferLater(reactor, consul.DEBOUNCE_PERIOD + 0.1, assertions)

    def test_debounce(self):
        """
        Test

        """
        change_nodes([
            ('test1', '192.168.1.1', 123),
            ('test3', '192.168.1.2', 125),
            ('test4', '192.168.1.3', 321),
        ])

        def first_test():
            compare = {
                ('192.168.1.3', 125),
                ('192.168.1.4', 321),
            }
            if client.connections != compare:
                raise AssertionError(
                    '{!r} != {!r}'.format(client.connections, compare)
                )

            # Change nodes for second test
            change_nodes([
                ('test1', '192.168.1.1', 123),
                ('test3', '192.168.1.3', 125),
                ('test4', '192.168.1.4', 321),
            ])

        def second_test():
            compare = {
                ('192.168.1.3', 125),
                ('192.168.1.4', 321),
            }
            if client.connections != compare:
                raise AssertionError(
                    '{!r} != {!r}'.format(client.connections, compare)
                )

        d = deferLater(reactor, consul.DEBOUNCE_PERIOD * 2 / 3, first_test)
        return d.addCallback(lambda _: deferLater(
            reactor, consul.DEBOUNCE_PERIOD * 2 / 3, second_test
        ))

    d = deferLater(reactor, 0.1, test_setup)
    d.addCallback(lambda _: deferLater(reactor, 0.5, lambda: None))
    d.addCallback(test_change)
    d.addCallback(lambda _: deferLater(reactor, 0.5, lambda: None))
    d.addCallback(test_debounce)

    def errback(err):
        # On error, print and then exit with a 2
        reactor.stop()
        err.printTraceback()
        import sys
        sys.exit(2)

    d.addCallback(lambda _: reactor.stop())
    d.addErrback(errback)

    reactor.run()
