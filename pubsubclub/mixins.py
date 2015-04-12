"""
The following classes are mixins in for a subclass of
:class:`autobahn.wamp1.protocol.WampServerFactory`.  Using these mixins
integrates PubSubClub into your WAMP application.

"""
import logging

from autobahn.wamp1 import protocol as wamp


class ProducerMixin(wamp.WampServerFactory):
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
        logging.info('Received dispatch, distributing to nodes.')
        self.producer.publish(topic, event)
        return wamp.WampServerFactory.dispatch(
            self, topic, event, exclude, eligible,
        )


class ConsumerMixin(wamp.WampServerFactory):
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
        logging.info('Received subscription request for %s'.format(topic))
        if self.subscriptions[topic] == 1:  # First subscription
            logging.info('Forwarding subscription to producers.')
            self.consumer.subscribe(topic)
        else:
            logging.info('Already subscribed on producers.  Ignoring request.')

    def onClientUnsubscribed(self, protocol, topic):
        """
        When a user has unsubscribed, check to see if it's the last user
        subscribed to the topic.  If it is, send a subscription request to the
        producer.

        """
        logging.info('Received unsubscription request for %s'.format(topic))
        if topic not in self.subscriptions:
            logging.info('Forwarding unsubscription to producers.')
            self.consumer.unsubscribe(topic)
        else:
            logging.info('Still some subscribed users.  Ingoring request.')
