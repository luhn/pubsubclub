import json

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

    def onOpen(self):
        """
        When a connection is made, remove node from ``starting_nodes`` (if
        applicable) and put it in ``nodes``

        """
        print('Made')
        self.factory.nodes.add(self)

    def onClose(self, *args):
        """
        When the connection is lost, remove nodes from the list.

        """
        print('Lost')
        print(args)
        self.factory.nodes.discard(self)
        self.factory.ready_nodes.discard(self)

    def onMessage(self, payload, is_binary):
        """
        Receive and parse an incoming action.

        """
        print('Message')
        obj = json.loads(payload)
        action, params = obj[0], obj[1:]
        callback = self.CALLBACK_MAP[action]
        getattr(self, callback)(*params)

    def send(self, action, *params):
        """
        Trigger an action to send to the other party.

        """
        print('Send')
        serialized = json.dumps([action] + params)
        self.sendMessage(serialized)

    def ready(self):
        """
        Mark this connection as having successfully shook hands.

        """
        print('Ready')
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


class ClientBase(object):
    #: The client factory.  Use for connecting to a server.
    factory = None

    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: Nodes that have completed the PubSubClub Protocol handstake.  Subset of
    #: :ivar:`nodes`
    ready_nodes = None

    def __init__(self, nodes=tuple()):
        self.factory.container = self
        self.nodes = set()
        self.ready_nodes = set()
        for host, port in nodes:
            self.connect(host, port)

    def connect(self, host, port):
        url = 'ws://{}:{}/'.format(host, port)
        factory = self.factory(url, debug=True)
        websocket.connectWS(factory)


class ServerBase(websocket.WebSocketServerFactory):
    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: Nodes that have completed the PubSubClub Protocol handstake
    ready_nodes = None

    def __init__(self, interface, port):
        self.nodes = set()
        self.ready_nodes = set()
        url = 'ws://{}:{}/'.format(interface, port)
        websocket.WebSocketServerFactory.__init__(self, url, debug=True, debugCodePaths=True)
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
