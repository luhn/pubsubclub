import logging
import json
from urlparse import urlsplit, urlunsplit
from urllib import urlencode

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers


POLL_WAIT = '10s'  #: The duration to longpoll


class ConsulDiscovery(object):
    def __init__(self, consul_url, consul_service, client):
        logging.info('ConsulDiscovery: Initializing')
        self.client = client
        self.consul_url = urlsplit(consul_url)[:2]
        self.consul_service = consul_service
        self.nodes = set()
        self.index = None
        self.self = None

    def start(self):
        logging.info('ConsulDiscovery:  Starting')
        d = self._query_self()  # Who are we?
        d.addCallback(lambda _: self._query_services())  # Get initial list
        d.addCallback(self.requeue)

    def requeue(self, _=None):
        d = self._query_services(wait=POLL_WAIT)
        d.addCallback(self.requeue)
        d.addErrback(self._handle_api_error)

    def _handle_api_error(self, failure):
        failure.printTraceback()
        deferLater(reactor, 10.0, self.requeue)

    def _query_self(self):
        logging.info('ConsulDiscovery:  Querying for self.')
        agent = Agent(reactor)
        url = urlunsplit(
            self.consul_url +
            ('/v1/agent/self', '', '')
        )
        d = agent.request(
            'GET', url,
            Headers({}),
            None,
        )
        return d.addCallback(readBody).addCallback(json.loads)\
            .addCallback(self._process_self)

    def _process_self(self, result):
        logging.info('ConsulDiscovery:  Received response:  %s', repr(result))
        self.self = result['Member']['Name']
        logging.info('ConsulDiscovery:  Set self to %s', self.self)

    def _query_services(self, wait=None):
        logging.info(
            'ConsulDiscovery:  Querying services with wait of %s',
            wait or 'None',
        )
        agent = Agent(reactor)
        if wait:
            params = {
                'wait': wait,
            }
        else:
            params = {}
        url = urlunsplit(
            self.consul_url +
            ('/v1/catalog/service/{}'.format(self.consul_service),
             urlencode(params), '')
        )
        if self.index:
            logging.info('ConsulDiscovery:  Index is %i', self.index)
            headers = {
                'X-Consul-Index': [str(self.index)],
            }
        else:
            headers = {}
        d = agent.request(
            'GET', url,
            Headers(headers),
            None,
        )

        return d.addCallback(self._get_new_index).addCallback(readBody)\
            .addCallback(json.loads).addCallback(self._process_services)

    def _get_new_index(self, response):
        header = response.headers.getRawHeaders('X-Consul-Index')
        if header:
            self.index = int(header[0])
            logging.info('ConsulDiscovery:  New index is %i', self.index)
        else:
            logging.info('ConsulDiscovery:  No new index.')
        return response

    def _process_services(self, result):
        logging.info('ConsulDiscovery:  Received response:  %s', repr(result))
        new_nodes = {
            (service['Address'], service['ServicePort']) for service in result
            if service['Node'] != self.self
        }
        # Nodes that have appeared
        for node in new_nodes - self.nodes:
            logging.info('ConsulDiscovery:  Connecting to %s:%s', *node)
            self.client.connect(*node)
        # Nodes that have disappeared
        for node in self.nodes - new_nodes:
            logging.info('ConsulDiscovery:  Disconnecting from %s:%s', *node)
            self.client.disconnect(*node)
        self.nodes = new_nodes
