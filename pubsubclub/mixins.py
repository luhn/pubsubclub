"""
The following classes are mixins in for a subclass of
:class:`autobahn.wamp1.protocol.WampServerFactory`.  Using these mixins
integrates PubSubClub into your WAMP application.

"""
from twisted.python import log

from autobahn.wamp1 import protocol as wamp


class ProducerMixin:
    """
    A mixin to integrate a producer into the application.  Subclass this
    alongside :class:`autobahn.wamp1.protocol.WampServerFactory`.

    """
    #: This should point to your :class:`pubsubclub.ProducerClient` or
    #: :class`pubsubclub.ProducerServer`.
    producer = None

    def dispatch(self, topic, event, exclude=[], eligible=None):
        """
        A PubSub message has been dispatched.  We need to send it out to all
        the other nodes with subscribed users.

        """
        log.msg('Received dispatch, distributing to nodes.')
        self.producer.publish(topic, event)
        return wamp.WampServerFactory.dispatch(
            self, topic, event, exclude, eligible,
        )


class ConsumerMixin:
    """
    A mixin to integrate a consumer into the application.  Subclass this
    alongside :class:`autobahn.wamp1.protocol.WampServerFactory`.

    Set the ``consumer`` instance variable to point to your
    :class:`pubsubclub.Consumer`.

    """
    #: This should point to your :class:`pubsubclub.ConsumerClient` or
    #: :class:`pubsubclub.ConsumerServer`.
    consumer = None

    def onClientSubscribed(self, protocol, topic):
        """
        When a user has subscribed, check to see if it's the first
        subscription.  If it is, send a subscription request to the producers.

        """
        log.msg('Received subscription request for %s', topic)
        if len(self.subscriptions[topic]) == 1:  # First subscription
            log.msg('Forwarding subscription to producers.')
            self.consumer.subscribe(topic)
        else:
            log.msg('Already subscribed on producers.  Ignoring request.')

    def onClientUnsubscribed(self, protocol, topic):
        """
        When a user has unsubscribed, check to see if it's the last user
        subscribed to the topic.  If it is, send a subscription request to the
        producer.

        """
        log.msg('Received unsubscription request for %s', topic)
        if topic not in self.subscriptions:
            log.msg('Forwarding unsubscription to producers.')
            self.consumer.unsubscribe(topic)
        else:
            log.msg('Still some subscribed users.  Ingoring request.')
