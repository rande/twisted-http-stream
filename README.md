# Twisted HTTP Stream

The ``twistedhttpstream`` package provides an event-driven API for receiving updates through the asynchronous HTTP Streaming API


## Notes

 - A JSON parser is required. Like `json <http://docs.python.org/library/json.html>`_ or `simplejson <http://pypi.python.org/pypi/simplejson/>`_.
 - All methods will automatically reconnect to the server with an exponential back-off. See `t.i.p.ReconnectingClientFactory <http://twistedmatrix.com/documents/8.2.0/api/twisted.internet.protocol.ReconnectingClientFactory.html>`_ for details.
 - All methods must be initialized with a *consumer* object, inherited from `twistedhttpstream.MessageReceiver`
 - No proxy support.

## Credits


Thanks to (in no particular order):

- Alexandre Fiori <fiorix@gmail.com>

  - The original author

- Arnaldo Moraes
  
  - Testing, patching and using for private projects

- Vanderson Mota

  - Patching setup.py and PyPi maintenance

## Usage


```python

    import twistedhttpstream
    from twisted.internet import reactor

    class consumer(twistedhttpstream.MessageReceiver):
        def connectionMade(self):
            print "connected..."

        def connectionFailed(self, why):
            print "cannot connect:", why
            reactor.stop()

        def messageReceived(self, message):
            print "new message:", repr(message)

    if __name__ == "__main__":

        twistedhttpstream.stream(reactor, 'https://stream.myawesomesite.com', consumer(), username="", password="")
        reactor.run()
```