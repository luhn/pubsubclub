import json
from urlparse import urlsplit, urlunsplit
from urllib import urlencode
from time import time as unix_timestamp

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.defer import Deferred, CancelledError, maybeDeferred
from twisted.python import log
from twisted.python.failure import Failure
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers


POLL_WAIT = '60s'  #: The duration to longpoll
DEBOUNCE_PERIOD = 30.0  # How long to wait before applying changes
MIN_QUERY_PERIOD = 5.0  # Throttle polling if it returns too quickly


class Debouncer(object):
    """
    An object to debounce a function.  Calling a function wrapped in this will
    delay the call for up to ``period`` seconds.  Further calls within that
    time period will overwrite the previous call.

    """
    def __init__(self, func):
        self.func = func
        self.wait = None
        self.last_args = None
        self.last_kwargs = None

    def __get__(self, obj, type=None):
        def func(*args, **kwargs):
            # If we haven't debounced
            if self.wait is None:
                log.msg('Starting debounce wait.')
                self.wait = deferLater(reactor, DEBOUNCE_PERIOD, self._call)

            log.msg('Args on deck: %s, %s', repr(args), repr(kwargs))
            self.last_obj = obj
            self.last_args = args
            self.last_kwargs = kwargs

        return func

    def _call(self):
        # Need to set these up here because the function call might be
        # recursive, triggering another debounce call.
        obj = self.last_obj
        args = self.last_args
        kwargs = self.last_kwargs
        log.msg(
            'Running function with args: %s, %s', repr(args), repr(kwargs),
        )
        self.wait = None
        self.last_args = None
        self.last_kwargs = None
        self.last_obj = None
        self.func(obj, *args, **kwargs)


class HTTPResponse(object):
    """
    Represents an HTTP response.

    :param body:  The body of the response.
    :type body:  str
    :param headers:  The headers of the response.
    :type headers:  dict

    """
    _json = None

    def __init__(self, body, headers):
        self.body = body
        self.headers = headers

    @classmethod
    def from_response(cls, response):
        """
        Create an object from the raw response.

        :param response:  The response from an HTTP request.
        :type response:  :class:`twisted.web.client.Response`

        :returns:  A Deferred which will fire with the response object.

        """
        headers = {
            key: value[0] for key, value in response.headers.getAllRawHeaders()
        }
        log.msg('Receiving response with headers:  %s', repr(headers))
        log.msg(headers)
        d = readBody(response)
        return d.addCallback(lambda body: cls(body, headers))

    @property
    def json(self):
        """
        Parse the body as JSON.

        """
        if self._json is None:
            self._json = json.loads(self.body)
        return self._json

    def __str__(self):
        return (
            'Headers: {!r}\nBody: {}'.format(self.body, self.headers)
        )

    def __repr__(self):
        return str(self)


def http_request(method, url, headers=dict()):
    """
    Make an HTTP request and return the entire response (with headers).

    :param method:  The request method.  One of GET, POST, PUT, or DELETE.
    :type method:  str
    :param url:  The URL to make a request to.
    :type url:  str
    :param headers:  The headers to send with the request.
    :type headers:  dict

    :returns:  A deferred which will callback with a :class:`HTTPResponse`

    """
    log.msg('Making %s request to %s', method, url)
    agent = Agent(reactor)
    request = agent.request(
        method,
        url,
        Headers({}),
        None,
    )
    return request.addCallback(HTTPResponse.from_response)


def retry_on_failure(wait, func, *args, **kwargs):
    """
    Retry if the deferred fails.

    :param wait:  Seconds to wait before trying again.
    :type wait:  float
    :param func:  The function to execute.
    :type func:  Callable.

    :returns:  A Deferred that will return with the succeeded call.

    """
    response = Deferred()

    def call():
        log.msg('Making call with retry.')
        d = maybeDeferred(func, *args, **kwargs)
        d.addCallback(response.callback)
        d.addErrback(retry)

    def retry(failure):
        log.msg('HTTP:  Failed with %s, retrying...', failure)
        reactor.callLater(wait, call)

    def callback(result):
        log.msg('Called back.')
        return result

    response.addCallback(callback)
    call()
    return response


class TimeoutError(Exception):
    pass


def deferred_timeout(deferred, timeout):
    """
    If the deferred takes too long, attempt to cancel it and raise an error.

    :param deferred:  The deferred to monitor.
    :type deferred:  :class:`twisted.internet.defer.Deferred`
    :param timeout:  Seconds to wait before cancelling the deferred
    :type timeout:  float

    :raises TimeoutError:  if the deferred times out.

    """
    d = Deferred()
    deferred.chainDeferred(d)

    def trigger_timeout():
        log.msg('HTTP:  Timeout reached, raising error.')
        d.errback(Failure(TimeoutError(), TimeoutError))

    def callback(result):
        log.msg('HTTP:  Response received before timeout.')
        delay.cancel()
        return result

    log.msg('Setting timeout for call.')
    delay = reactor.callLater(timeout, trigger_timeout)
    return d.addBoth(callback)


class ConsulDiscovery(object):
    def __init__(self, consul_url, consul_service, client):
        log.msg('ConsulDiscovery: Initializing')
        self.client = client
        self.consul_url = urlsplit(consul_url)[:2]
        self.consul_service = consul_service
        self.nodes = set()
        self.index = None
        self.self = None
        self.last_queued = 0.0

    def start(self):
        log.msg('ConsulDiscovery:  Starting')
        d = self._query_self()  # Who are we?
        d.addCallback(lambda _: self._query_services())  # Get initial list
        d.addCallback(self.requeue)
        d.addErrback(self._print_traceback)
        return d

    def _print_traceback(self, result):
        result.printTraceback()
        return result

    def requeue(self, _=None):
        run = lambda: self._query_services(wait=POLL_WAIT, debounce=True)
        if unix_timestamp() - self.last_queued < MIN_QUERY_PERIOD:
            d = deferLater(reactor, MIN_QUERY_PERIOD, run)
        else:
            d = run()
        self.last_queued = unix_timestamp()
        d.addCallback(self.requeue)
        d.addErrback(self._handle_api_error)

    def _handle_api_error(self, failure):
        failure.printTraceback()
        deferLater(reactor, 10.0, self.requeue)

    def _query_self(self):
        log.msg('ConsulDiscovery:  Querying for self.')
        url = urlunsplit(
            self.consul_url +
            ('/v1/agent/self', '', '')
        )
        d = retry_on_failure(
            10.0,
            lambda: deferred_timeout(http_request('GET', url), 10.0),
        )

        d.addCallback(self._process_self)

        def callback(result):
            log.msg('%s', result)
            return result

        return d

    def _process_self(self, result):
        log.msg('Right before error.')
        result = result.json
        log.msg('ConsulDiscovery:  Received response:  %s', repr(result))
        self.self = result['Member']['Name']
        log.msg('ConsulDiscovery:  Set self to %s', self.self)

    def _query_services(self, wait=None, debounce=False):
        log.msg(
            'ConsulDiscovery:  Querying services with wait of %s',
            wait or 'None',
        )
        params = {
            'passing': '',
            'pretty': '',
        }
        if wait:
            params['wait'] = wait
        if self.index:
            params['index'] = self.index
        url = urlunsplit(
            self.consul_url +
            ('/v1/health/service/{}'.format(self.consul_service),
             urlencode(params), '')
        )
        log.msg('ConsulDiscovery:  URL is %s', url)
        d = retry_on_failure(
            10.0,
            http_request,
            'GET',
            url,
        )

        callback = (
            self._process_services_debounced if debounce
            else self._process_services
        )

        return d.addCallback(self._get_new_index).addCallback(callback)

    def _get_new_index(self, response):
        log.msg(response.headers)
        header = response.headers.get('X-Consul-Index')
        if header:
            self.index = int(header)
            log.msg('ConsulDiscovery:  New index is %i', self.index)
        else:
            log.msg('ConsulDiscovery:  No new index.')
        return response

    def _process_services(self, result):
        result = result.json
        log.msg('ConsulDiscovery:  Received response:  %s', repr(result))
        new_nodes = {
            (
                service['Node']['Address'], service['Service']['Port'],
            ) for service in result if service['Node']['Node'] != self.self
        }
        log.msg('ConsulDiscovery:  Nodes:  %s', repr(new_nodes))
        # Nodes that have appeared
        for node in new_nodes - self.nodes:
            log.msg('ConsulDiscovery:  Connecting to %s:%s', *node)
            self.client.connect(*node)
        # Nodes that have disappeared
        for node in self.nodes - new_nodes:
            log.msg('ConsulDiscovery:  Disconnecting from %s:%s', *node)
            self.client.disconnect(*node)
        self.nodes = new_nodes

    _process_services_debounced = Debouncer(_process_services)
