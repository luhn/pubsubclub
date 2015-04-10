# PubSubClub Protocol specification (v0.1.0)

The PubSubClub Protocol implements a simple publish-subscribe messaging system
among a cluster of nodes.  It is intended for use with PubSubClub, a Python
mixin for Autobahn|Python's WAMPv1, in order to distribute WAMP PubSubs to all
users, regardless of what node they are connected to.

This protocol specification is versioned using [Semantic
Versioning](http://semver.org/).

## Roles

The protocol defines two roles, *producer* and *consumer*.  The producer will
distribute PubSub messages published via WAMP to the consumers, and the
consumers will then distribute the messages to the users subscribed via WAMP.
An application may fill the roles of both consumer and producer.

## The protocol

All messages are JSON-encoded arrays.  The first item of the array is an
integer indicating the message type and the remaining items (if any) are
parameters for that message.  The messages are as follows.

### 1xx — Handshake

#### PSC101 — Declare implemented versions

Sent by:  Producer, Consumer

Declare the the version of the PubSubClub Protocol that the implementation
supports.  Each supported version is sent as a parameter, serialized as an
two-item array containing the major version number and the minor veresion
number.  (Patch version numbers are ignored.)

Parameters:  version (array), version (array), version (array), ...

#### PSC102 — Choose version

Sent by:  Producer, Consumer

After a party has declared implemented versions (PSC101), the opposing party
selects which version the connection will use.  The highest mutually-supported
version should be selected.  The version parameter is serialized in the same
format as PSC101.

Parameters:  version (array)

### 2xx — Subscription

#### PSC201 — Subscribe

Sent by:  Consumer

Instruct the producer to begin sending all messages for the given topic(s).

Parameters:  topic (string), topic (string), topic (string), ...

#### PSC202 — Unsubscribe

Sent by:  Consumer

Instruct the producer to stop sending messages for the given topic.

Parameters:  topic (string)

### 3xx — Publication

#### PSC301 — Publish

Sent by:  Producer

Send a PubSub message to the consumer for distribution.

Parameters:  topic (string), message (any object)

## Lifecycle

Either the producers or consumers can behave as servers.  The other role will
behave as clients.  The behavior must be consistent across the entire role.
The clients should be furnished a list, either manually or with a discovery
service such as [consul](http://consul.io), and each client should make a
connection to each server.

Upon making a connection, the consumer (regardless of whether the client or the
server) then sends PSC101, to which the producer sends PSC102 in response.
Once the PSC102 is received, the handshake is complete, and the consumer should
send over all of the topics it is currently subscribed to, if any.

Each time a pubsub is triggered on a producer, the producer should send PSC301
to consumer that has subscribed to the topic, if any.  Each time
an end user subscribes to a new topic that the corresponding consumer has not
yet subscribed to, it should send a PSC201 to all connected producers.  If a
end user unsubscribes from a topic, leaving no other end users subscribed to
that topic, the consumer should send a PSC202 to all connected producers.

Every five seconds, the client should send a WebSocket *ping*, to which the
server should immediately reply with a *pong*.  If a *pong* is not received
before the next *ping*, the connection should be assumed to be broken, and the
discovery application should attempt a reconnect.  A reconnect should continue
to be tried approximately every second.  Jitter or an exponential backoff may
be introduced.

## Discovery

An implementation of a client should include methods to add and remove servers
during operation, which could be hooked up to a discovery service, such as
[consul](http://consul.io).  Upon adding a server, a connection should
immediately be established and the lifecycle begin.  Upon removing a server,
the connection should be closed and the server removed from the client's list
of servers.
