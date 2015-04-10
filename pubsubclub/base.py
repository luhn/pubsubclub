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

    def connectionMade(self):
        """
        When a connection is made, remove node from ``starting_nodes`` (if
        applicable) and put it in ``nodes``

        """
        self.factory.nodes.add(self)

    def connectionLost(self):
        """
        When the connection is lost, remove nodes from the list.

        """
        self.factory.nodes.remove(self)
        self.factory.ready_nodes.discard(self)

    def onMessage(self, payload, is_binary):
        """
        Receive and parse an incoming action.

        """
        obj = json.loads(payload)
        action, params = obj[0], obj[1:]
        callback = self.CALLBACK_MAP[action]
        getattr(self, callback)(*params)

    def send(self, action, *params):
        """
        Trigger an action to send to the other party.

        """
        serialized = json.dumps([action] + params)
        self.sendMessage(serialized)

    def ready(self):
        """
        Mark this connection as having successfully shook hands.

        """
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
        pass


class ServerBase(websocket.WebSocketServerFactory):
    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: Nodes that have completed the PubSubClub Protocol handstake
    ready_nodes = None

    def __init__(self, interface, port):
        self.nodes = set()
        self.ready_nodes = set()
        super(ServerBase, self).__init__()  # TODO:  Initialize factory


def make_client(name, class_, protocol):
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
        (class_, ClientBase),
        {'factory': Factory},
    )
    return Client


def make_server(name, class_, protocol):
    Protocol = type(
        'ServerBase',
        (protocol, websocket.WebSocketServerProtocol),
        dict(),
    )
    Server = type(
        'Server',
        (class_, ServerBase),
        {'protocol': Protocol},
    )
    return Server
