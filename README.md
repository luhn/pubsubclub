# PubSubClub

PubSubClub is an Autobahn|Python mixin for distributing WAMPv1 PubSubs among a
cluster of instances, a necessity for an WAMP service that has to run on two
or more nodes for scaling or high availability purposes.

## Supported Software

PubSubClub only supports WAMPv1 at the moment, and therefore Autobahn|Python <=
1.8.15, because WAMPv1 support was removed in 0.9.0.  Unfortunately, I have
little motivation to support WAMPv2 because Autobahn|Android does not yet
support WAMPv2, so I am prevented from upgrading.

You can either manually define the nodes in your cluster, or use discover them
using the [Consul](http://consul.io/).  However, it should be easy to extend it
to use your favorite service discovery should you desire to.
