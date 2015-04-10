"""
The following classes are mixins in for a subclass of
:class:`autobahn.wamp1.protocol.WampServerFactory`, which will integrate
PubSubClub into the WAMP application.

"""
from autobahn.wamp1.protocol import WampServerFactory


class ProducerMixin(WampServerFactory):
    """
    A mixin to integrate a producer into the application.

    """
    #: This should point to your :class:`pubsubclub.Producer`.
    producer = None

    def dispatch(self, topic, event, exclude=[], eligible=None):
        """
        A PubSub message has been dispatched.  We need to send it out to all
        the other nodes with subscribed users.

        """
        self.producer.dispatch(topic, event)
        return super(WampServerFactory, self).dispatch(
            topic, event, exclude, eligible,
        )


class ConsumerMixin(WampServerFactory):
    """
    A mixin to integrate a consumer into the application.

    Set the ``consumer`` instance variable to point to your
    :class:`pubsubclub.Consumer`.

    """
    def onClientSubscribed(self, protocol, topic):
        """
        A user has subscribed!  We need to make sure we're subscribed to the
        topic.

        """
        if self.subscriptions[topic] == 1:  # First subscription
            self.consumer.subscribe(topic)

    def onClientUnsubscribed(self, protocol, topic):
        """
        A user has unsubscribed!  If it's the last user subscribed to that
        topic, we need to unsubscribe.

        """
        if topic not in self.subscriptions:
            self.consumer.unsubscribe(topic)
