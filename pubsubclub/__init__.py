from __future__ import absolute_import
import random

from .mixins import ProducerMixin, ConsumerMixin

from .consumer import ConsumerClient, ConsumerServer
from .producer import ProducerClient, ProducerServer


def generate_id():
    """
    Generate an ID suitable for use with Pubsubclub.

    """
    return random.randrange(2**31)


__all__ = [
    'ProducerMixin',
    'ConsumerMixin',
    'ConsumerClient',
    'ConsumerServer',
    'ProducerClient',
    'ProducerServer',
    'generate_id',
]
