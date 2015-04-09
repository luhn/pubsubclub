# PubSubClub

PubSubClub is an Autobahn|Python mixin for distributing WAMPv1 PubSubs among a
cluster of instances, a necessity for an WAMP service that has to run on two
or more nodes for scaling and/or high availability.

## Supported Software

PubSubClub only supports WAMPv1 at the moment, and therefore Autobahn|Python <=
1.8.15, because WAMPv1 support was removed in 0.9.0.  Unfortunately, I have
little motivation to support WAMPv2 because Autobahn|Android does not yet
support WAMPv2, so I am prevented from upgrading.

You can either manually define the nodes in your cluster, or use discover them
using the [Consul](http://consul.io/).  However, it should be easy to extend it
to use your favorite service discovery should you desire to.

## Design

PubSubClub is very simple.  It uses WAMP's own PubSub implementation to
distribute the PubSubs among the cluster.  This makes the implementation very
accessible to the target audience, people using WAMP.

There are two roles an application can take:  *publisher* and *consumer*.  A
publisher (a WAMP client) distributes PubSubs to many consumers (WAMP servers).
An application may fill the roles of both consumer

PubSubClub is meant to be embedded into a WAMP application.  It does not
require additional processes or servers, and has no dependencies beyond
Autobahn|Python and Twisted.
