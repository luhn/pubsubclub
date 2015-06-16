import json
from weakref import WeakSet

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

    #: Set to true after handshake is completed.
    ready = False

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
        log.msg('Lost connection!  Discarding self from nodes.')
        self.factory.nodes.discard(self)
        if clean:
            log.msg('Connection was closed cleanly.')
            self.factory.clean_close = True

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
        self.ready = True


class ClientFactory(
    websocket.WebSocketClientFactory,
    ReconnectingClientFactory,
    object,
):
    #: Indicates whether the closure was clean or not.  We attempt a reconnect
    #: on unclean closures.
    clean_close = False

    def clientConnectionFailed(self, connector, reason):
        """
        If we fail to connect, try try again.

        """
        if not self.clean_close:
            log.msg("Connection failed, attempting to reconnect.")
            self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        """
        If we lose the connection, attempt to reestablish it.

        """
        if not self.clean_close:
            log.msg("Connection lost, attempting to reconnect.")
            self.retry(connector)

    @property
    def nodes(self):
        return self.container.nodes


class ClientBase(object):
    #: The client factory.  Use for connecting to a server.
    factory = None

    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: For consumers only, a WAMP class which forwards consumed data to the end
    #: users.
    processor = None

    def __init__(self, nodes=tuple()):
        self.factory.container = self
        self.nodes = WeakSet()
        for host, port in nodes:
            self.connect(host, port)

    def connect(self, host, port):
        """
        Make a connection to a server.

        """
        url = 'ws://{}:{}/'.format(host, port)
        log.msg('Connecting to %s' % url)
        websocket.connectWS(self.factory(url))

    def disconnect(self, host, port):
        """
        Lose a previously made connection.

        """
        for node in self.nodes:
            if node.factory.host == host and node.factory.port == port:
                node.sendClose()


class ServerBase(websocket.WebSocketServerFactory, object):
    #: A :class:`set` of :class:`ProtocolBase` for each connection to a node.
    nodes = None

    #: For consumers only, a WAMP class which forwards consumed data to the end
    #: users.
    processor = None

    def __init__(self, interface, port):
        self.nodes = WeakSet()
        url = 'ws://{}:{}/'.format(interface, port)
        log.msg('Listening on %s' % url)
        websocket.WebSocketServerFactory.__init__(self, url)
        websocket.listenWS(self)


def passthrough_factory(name):
    """
    A factory for methods that will pass the call onto all the nodes.

    """
    def method(self, *args, **kwargs):
        for node in self.nodes:
            getattr(node, name)(*args, **kwargs)

    return method


def make_client(name, passthrough, protocol):
    """
    Create a WebSocket client container (subclass of :class:`ClientBase`),
    subclassing from the given class.

    :param passthrough:  A list of methods to passthrough to the protocol.
    :type passthrough:  list of str
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

    attrs = {
        'factory': Factory,
    }
    for method in passthrough:
        attrs[method] = passthrough_factory(method)
    Client = type(
        'Client',
        (ClientBase,),
        attrs,
    )
    return Client


def make_server(name, passthrough, protocol):
    """
    Create a WebSocket server factory (subclass of :class:`ServerBase`),
    subclassing from the given class.

    :param passthrough:  A list of methods to passthrough to the protocol.
    :type passthrough:  list of str
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

    attrs = {
        'protocol': Protocol,
    }
    for method in passthrough:
        attrs[method] = passthrough_factory(method)
    Server = type(
        'Server',
        (ServerBase,),
        attrs,
    )
    return Server
