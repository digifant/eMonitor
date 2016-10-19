from ws4py.websocket import WebSocket
import json
import logging
import traceback

logger = logging.getLogger(__name__)
logger.setLevel (logging.DEBUG)

if not 'SUBSCRIBERS' in globals():
    SUBSCRIBERS = set()  # set holds all active connections

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


class SocketHandler(WebSocket):
    """
    handler for socketserver to deliver messages
    """
    def __init__(self, *args, **kw):
        WebSocket.__init__(self, *args, **kw)
        global SUBSCRIBERS
        SUBSCRIBERS.add(self)
        logger.debug('SocketHandler __init__ subscriber set=%s' % SUBSCRIBERS )

    def closed(self, code, reason=None):
        global SUBSCRIBERS
        SUBSCRIBERS.remove(self)

    @staticmethod
    def send_message(payload, **extra):
        global SUBSCRIBERS
        logger.debug('SocketHandler send message=%s' % payload )
        if extra:
            extra['sender'] = payload
            payload = json.dumps(extra)
        try:    
            for subscriber in SUBSCRIBERS:
                subscriber.send(payload)
        except RuntimeError:
            logger.error ( traceback.format_exc() )

    def received_message(self, message):
        global SUBSCRIBERS
        logger.debug('SocketHandler received message=%s' % message )
        for subscr in SUBSCRIBERS:
            subscr.send(message.data, message.is_binary)
