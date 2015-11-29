import os.path
import os
from time import sleep
import socket
from zope.interface import implements

from kivy.support import install_twisted_reactor
install_twisted_reactor()

from twisted.internet import protocol, reactor, defer, interfaces

CHUNKSIZE = 1024


def get_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(('<broadcast>', 0))
    return s.getsockname()[0]


class SendProducer(object):
    implements(interfaces.IPushProducer)

    def __init__(self, transport, finput):
        self._transport = transport
        self._finput = finput
        self._count = os.fstat(finput.fileno()).st_size
        self._produced = 0
        self._paused = False

    def pauseProducing(self):
        self._paused = True

    def resumeProducing(self):
        self._paused = False

        while not self._paused and self._produced < self._count:
            self._transport.write(self._finput.read(CHUNKSIZE))
            self._produced += CHUNKSIZE

        if self._produced >= self._count:
            self._transport.unregisterProducer()
            self._transport.loseConnection()
            # this should be in a 'finally' 
            self._finput.close()

    def stopProducing(self):
        self._produced = self._count


class SendingException(Exception):
    pass


class ReceiveProto(protocol.Protocol):
    def dataReceived(self, data):
        self.factory.data_writer(data)

    def connectionLost(self, reason):
        print 'losing connection'
        print self.factory.received
        print reason
        # self.factory.received.callback(reason)
        self.factory.received.callback('no reason')


class ReceiveFactory(protocol.Factory):
    protocol = ReceiveProto

    def __init__(self, data_writer, received):
        print 'ready to recv'
        self.data_writer = data_writer
        self.received = received


class SendProto(protocol.Protocol):
    def connectionMade(self):
        print 'connectionMade!'
        # self.factory.sender.on_connection(self.transport)
        self.factory.sender.callback(self.transport)


class SendFactory(protocol.ClientFactory):
    protocol = SendProto

    def __init__(self, sender):
        self.sender = sender

    def clientConnectionLost(self, conn, reason):
        print 'lost'
        # reactor.stop()

    def clientConnectionFailed(self, conn, failure):
        print 'failed'
        pass
        # reactor.stop()


class Sender(object):
    # make into context manager?
    # all this is done with call backs
    # how about switched to deferreds?
    def __init__(self, ip, port):
        self.transport = None
        self.dest_ip = ip
        self.dest_port = int(port)
        self.filepath = None
        self.send = defer.Deferred()
        self.send.addCallback(self.on_connection)

    def on_connection(self, transport):
        self.transport = transport

        f = open(self.filepath, 'rb')
        producer = SendProducer(transport, f)
        transport.registerProducer(producer, True)
        producer.resumeProducing()

    def sendFile(self, filepath):
        self.filepath = filepath
        reactor.connectTCP(self.dest_ip, self.dest_port, SendFactory(self.send))


class Receiver(object):
    def __init__(self, port):
        self.transport = None
        self.src_port = int(port)
        self.filepath = None
        self.listener = None
        self.created = False
        self.data = []

        self.received = defer.Deferred()
        self.received.addCallback(self.transfer_done)

    def transfer_done(self, reason):
        # dont work with big files
        print reason
        self.listener.stopListening()
        print 'all done'
        # handle errors/bad connections

    def receiveFile(self, filepath):
        self.filepath = filepath

        def data_writer(data):
            # if not os.path.exists(self.filepath) or self.created:
            with open(self.filepath, 'ab') as f:
                f.write(data)

        self.listener = reactor.listenTCP(self.src_port, ReceiveFactory(data_writer, self.received))
