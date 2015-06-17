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

You can either manually define the nodes in your cluster, or use discover them
using the [Consul](http://consul.io/).  However, it should be easy to extend it
to use your favorite service discovery should you desire to.

## Overview

Each node in a PubSubClub cluster is a _producer_ or _consumer_ or both.
Consumers and producers communicate with eachother via [a simple
WebSocket](SPEC.md) protocol, the consumers informing the producers what pubsub
topics they're interested in and the producers broadcasting relevant pubsubs to
the consumers.

Either the producers or the consumers must behave as a WebSocket client and the
other behave as a TCP server.  This must be consistent across the entire
cluster.

## Scalability

Each PubSubClub client makes a connection to each PubSubClub server.  Usually
each application node implements both a client and a server, so the number of
connections increase exponentially with the number of nodes, making PubSubClub
unsuitable for a very large clusters.  Also, each PubSub is sent directly to
each subscribed node, so in a large cluster where all or most nodes are
subscribed to a topic, publishing to that topic would put a large burden on
the publisher's network and potentially slow the distribution of the pubsub.

TL;DR:  If you have a large number of nodes, PubSubClub is not for you.
