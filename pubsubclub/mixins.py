"""
The following classes are mixins in for a subclass of
:class:`autobahn.wamp1.protocol.WampServerFactory`.  Using these mixins
integrates PubSubClub into your WAMP application.

"""


class ProducerMixin(object):
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
        self.producer.dispatch(topic, event)
        return super(ProducerMixin, self).dispatch(
            topic, event, exclude, eligible,
        )


class ConsumerMixin(object):
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
        subscription.  If it is, send a subscription request to the publishers.

        """
        if self.subscriptions[topic] == 1:  # First subscription
            self.consumer.subscribe(topic)

    def onClientUnsubscribed(self, protocol, topic):
        """
        When a user has unsubscribed, check to see if it's the last user
        subscribed to the topic.  If it is, send a subscription request to the
        publisher.

        """
        if topic not in self.subscriptions:
            self.consumer.unsubscribe(topic)
