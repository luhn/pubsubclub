# PubSubClub

PubSubClub is an Autobahn|Python mixin for distributing WAMPv1 PubSubs among a
cluster of instances, a necessity for an WAMP service that has to run on two
or more nodes for scaling and/or high availability.

## Supported Software

PubSubClub only supports WAMPv1 at the moment, and therefore Autobahn|Python <=
0.8.15, because WAMPv1 support was removed in 0.9.0.  Currently, I have little
motivation to support WAMPv2 because I do not personally use it yet, and WAMPv2
support for PubSubClub will be made obsolete by the [3.0 release of
Crossbar.io](http://crossbar.io/docs/Roadmap/), scheduled for release in August
2015.

Pubsubclub is also restricted to Twisted right now, but it would be possible
to expand to [asyncio](https://docs.python.org/3/library/asyncio.html) just
like Autobahn.

You can either manually define the nodes in your cluster, or use discover them
using the [Consul](http://consul.io/).  However, it should be easy to extend it
to use your favorite service discovery should you desire to.

## Installation

You can install PubSubClub from GitHub using pip.

```bash
pip install https://github.com/luhn/pubsubclub/archive/master.tar.gz
```

PubSubClub runs entirely within your WAMP application—You don't run any
additional programs.

## Overview

Each node in a PubSubClub cluster is a _producer_ or _consumer_ or both.
Consumers and producers communicate with eachother via [a simple
WebSocket](SPEC.md) protocol, the consumers informing the producers what pubsub
topics they're interested in and the producers broadcasting relevant pubsubs to
the consumers.

Either the producers or the consumers must behave as a WebSocket client and the
other behave as a TCP server.  This must be consistent across the entire
cluster.

### Setting up a consumer

To create a consumer, which will receive pubsubs from producers and forward
them to clients of the WAMP server, initialize an object of either
`pubsubclub.ConsumerServer` or `pubsubclub.ConsumerClient`.  `ConsumerServer`
takes the interface and port to listen on as arguments, e.g.:

```python
from pubsubclub import ConsumerServer
consumer = ConsumerServer('0.0.0.0', 19000)
```

A `ConsumerClient` takes a list of producer servers to connect to, like so:

```python
from pubsubclub import ConsumerClient
consumer = ConsumerClient([
    ('192.168.1.123', 19000),
    ('192.168.1.124', 19000),
])
```

Choose one or the other.  Then to hook it up to your WAMP application, mixin
`pubsubclub.ConsumerMixin` to your WAMP server factory and set the `consumer`
property as your `ConsumerClient` or `ConsumerServer` object.  You'll also need
to set the `processor` property in your consumer to the WAMP server factory
This might look something like this:

```python
from twisted.internet import reactor
from autobahn.twisted.websocket import listenWS
from autobahn.wamp1 import protocol as wamp
from pubsubclub import ConsumerMixin, ConsumerServer


class WampServerProtocol(wamp.WampServerProtocol):
    pass


class WampServerFactory(ConsumerMixin, wamp.WampServerFactory):
    protocol = WampServerProtocol


factory = WampServerFactory('ws://0.0.0.0:8080')
listenWS(factory)

consumer = ConsumerServer('0.0.0.0', 19000)
factory.consumer = consumer
consumer.processor = factory

reactor.run()
```

### Setting up a producer

You'll need to create a `ProducerClient` or `ProducerServer` on some nodes as a
counterpoint to your `ConsumerClient` or `ConsumerServer`.  If you made a
`ConsumerClient`, create a `ProducerServer` like so:

```python
from pubsubclub import ProducerServer
producer = ProducerServer('0.0.0.0', 19000)
```

Or, if you made a `ConsumerServer`, create a `ProducerClient` like this:

```python
from pubsubclub import ProducerClient
producer = ProducerClient([
    ('192.168.1.123', 19000),
    ('192.168.1.124', 19000),
])
```

Integrating this with your WAMP server is very similar to the consumer, but
you'll be using `pubsubclub.ProducerMixin` and you don't need to set a
`processor` property on the producer.

```python
from twisted.internet import reactor
from autobahn.twisted.websocket import listenWS
from autobahn.wamp1 import protocol as wamp
from pubsubclub import ProducerMixin, ProducerClient


class WampServerProtocol(wamp.WampServerProtocol):
    pass


class WampServerFactory(ProducerMixin, wamp.WampServerFactory):
    protocol = WampServerProtocol


factory = WampServerFactory('ws://0.0.0.0:8080')
listenWS(factory)

producer = ProducerClient([
    ('192.168.1.123', 19000),
    ('192.168.1.124', 19000),
])
factory.producer = producer

reactor.run()
```

### Setting up both a consumer and producer

Oftentimes a WAMP server will behave both as a producer, broadcasting pubsubs,
and as a consumer, subscribing to pubsub topics.  It's simple to combine the
producer and consumer code from above to make a WAMP server that fills both
roles.

```python
from twisted.internet import reactor
from autobahn.twisted.websocket import listenWS
from autobahn.wamp1 import protocol as wamp
from pubsubclub import (
    ConsumerMixin, ProducerMixin, ConsumerServer, ProducerClient,
)


class WampServerProtocol(wamp.WampServerProtocol):
    pass


class WampServerFactory(ConsumerMixin, ProducerClient, wamp.WampServerFactory):
    protocol = WampServerProtocol


factory = WampServerFactory('ws://0.0.0.0:8080')
listenWS(factory)

consumer = ConsumerServer('0.0.0.0', 19000)
factory.consumer = consumer
consumer.processor = factory

producer = ProducerClient([
    ('192.168.1.123', 19000),
    ('192.168.1.124', 19000),
])
factory.producer = producer

reactor.run()
```

## Node discovery

In the above examples, we hardcode into the clients what servers to connect to.
This obviously won't work well for the unstable topography of a
highly-available distribute system.

Right now PubSubClub supports node discovery via [Consul](consul.io).  Setting
this up is very simple.

```python
from pubsubclub import consul

discovery = consul.ConsulDiscovery(
    'http://localhost:18101/', 'consul', client,
)
discovery.start()
```

The arguments for `ConsulDiscovery` are respectively the URL for Consul's HTTP
API, the name of the service to query, and the producer or consumer client.

No other discovery services are implemented at this time.

## Scalability

Each PubSubClub client makes a connection to each PubSubClub server.  Usually
each application node implements both a client and a server, so the number of
connections increase exponentially with the number of nodes, making PubSubClub
unsuitable for a very large clusters.  Also, each PubSub is sent directly to
each subscribed node, so in a large cluster where all or most nodes are
subscribed to a topic, publishing to that topic would put a large burden on
the publisher's network and potentially slow the distribution of the pubsub.

TL;DR:  If you have a large number of nodes, PubSubClub is not for you.
