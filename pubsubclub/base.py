import json

from twisted.python import log
from twisted.internet.protocol import ReconnectingClientFactory

from autobahn.twisted import websocket


class ProtocolBase(object):
    """
    A base object for a protocol, client or server.

    """
    #: Map of call number and the corresponding callback
    CALLBACK_MAP = {
        101: 'onDeclaredVersions',
        102: 'onVersionChosen',
        201: 'onSubscribe',
        202: 'onUnsubscribe',
        301: 'onPublish',
    }

    def onConnect(self, request):
        """
        When a connection is made, remove node from ``starting_nodes`` (if
        applicable) and put it in ``nodes``

        """
        self.factory.nodes.add(self)

    def onClose(self, clean, code, reason):
        """
        When the connection is lost, remove nodes from the list.

        """
        log.msg(code)
        log.msg(reason)
        if not clean:
            log.msg('Lost connection!')
        else:
            log.msg('Connection closed.  Discarding self from nodes.')
        self.factory.nodes.discard(self)
        self.factory.ready_nodes.discard(self)

    def onMessage(self, payload, is_binary):
        """
        Receive and parse an incoming action.

        """
        log.msg('%s:  Received message:  %s', self.ROLE, payload)
        obj = json.loads(payload)
        action, params = obj[0], obj[1:]
        callback = self.CALLBACK_MAP[action]
        getattr(self, callback)(*params)

    def send(self, action, *params):
        """
        Trigger an action to send to the other party.

        """
        serialized = json.dumps([action] + list(params))
        log.msg('%s: Sending message:  %s', self.ROLE, serialized)
        self.sendMessage(serialized, False)

    def ready(self):
        """
        Mark this connection as having successfully shook hands.

        """
        log.msg('%s:  Marking connection as ready.', self.ROLE)
        self.factory.ready_nodes.add(self)


class ClientFactory(
    websocket.WebSocketClientFactory,
    ReconnectingClientFactory,
    object,
):
    def clientConnectionFailed(self, connector, reason):
        """
        If we fail to connect, try try again.

        """
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        """
        If we lose the connection, attempt to reestablish it.

        """
        self.retry(connector)

    @property
    def nodes(self):
        return self.container.nodes

    @property
    def ready_nodes(self):
        return self.container.ready_nodes

    @property
    def processor(self):
        return self.container.processor


class ClientBase(object):
    #: The client factory.  Use for connecting to a server.
    factory = None

    #: A :class:`dict` of :class:`ProtocolBase` for each connection to a node.
    connections = None

    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: Nodes that have completed the PubSubClub Protocol handstake.  Subset of
    #: :ivar:`nodes`
    ready_nodes = None

    #: For consumers only, a WAMP class which forwards consumed data to the end
    #: users.
    processor = None

    def __init__(self, nodes=tuple()):
        self.factory.container = self
        self.nodes = set()
        self.ready_nodes = set()
        self.connections = dict()
        for host, port in nodes:
            self.connect(host, port)

    def connect(self, host, port):
        """
        Make a connection to a server.

        """
        key = (host, port)
        if key in self.connections:
            log.msg(
                'Already connected to {}:{}!  Will not connect again.'
                .format(host, port)
            )
            return
        url = 'ws://{}:{}/'.format(host, port)
        log.msg('Connecting to %s' % url)
        factory = self.connections[(host, port)] = self.factory(url)
        websocket.connectWS(factory)

    def disconnect(self, host, port):
        """
        Lose a previously made connection.

        """
        try:
            self.connections[(host, port)].protocol.close()
        except KeyError:
            log.msg(
                'Could not find connection to {}:{}.'.format(host, port)
            )


class ServerBase(websocket.WebSocketServerFactory):
    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: Nodes that have completed the PubSubClub Protocol handstake
    ready_nodes = None

    #: For consumers only, a WAMP class which forwards consumed data to the end
    #: users.
    processor = None

    def __init__(self, interface, port):
        self.nodes = set()
        self.ready_nodes = set()
        url = 'ws://{}:{}/'.format(interface, port)
        log.msg('Listening on %s' % url)
        websocket.WebSocketServerFactory.__init__(self, url)
        websocket.listenWS(self)


def make_client(name, class_, protocol):
    """
    Create a WebSocket client container (subclass of :class:`ClientBase`),
    subclassing from the given class.

    :param class_:  The class to subclass the container from.
    :type class_:  type
    :param protocol:  The class to subclass the protocol from.
    :type protocol:  type

    :returns:  The WebSocket client container
    :rtype:  type

    """
    Protocol = type(
        'ClientProtocol',
        (protocol, websocket.WebSocketClientProtocol),
        dict(),
    )
    Factory = type(
        'ClientFactory',
        (ClientFactory,),
        {'protocol': Protocol},
    )
    Client = type(
        'Client',
        (ClientBase, class_),
        {'factory': Factory},
    )
    return Client


def make_server(name, class_, protocol):
    """
    Create a WebSocket server factory (subclass of :class:`ServerBase`),
    subclassing from the given class.

    :param class_:  The class to subclass the container from.
    :type class_:  type
    :param protocol:  The class to subclass the protocol from.
    :type protocol:  type

    :returns:  The WebSocket server factory
    :rtype:  type

    """
    Protocol = type(
        'ServerBase',
        (protocol, websocket.WebSocketServerProtocol),
        dict(),
    )
    Server = type(
        'Server',
        (ServerBase, class_),
        {'protocol': Protocol},
    )
    return Server
