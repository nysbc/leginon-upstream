#
# COPYRIGHT:
#       The Leginon software is Copyright under
#       Apache License, Version 2.0
#       For terms of the license agreement
#       see  http://leginon.org
#
DEBUG = False

class TransportError(IOError):
	pass

class ExitException(Exception):
	pass

from . import localtransport
from . import tcptransport

class Ping(object):
	pass

class Base(object):
	def __init__(self, logger):
		# order matters
		self.transportmodules = [localtransport, tcptransport]
		self.logger = logger

class Client(Base):
	'''
	Basic data transport client. It sends request to transportmodule
  server location and receives results handled.
	'''
	def __init__(self, serverlocation, logger):
		Base.__init__(self, logger)

		self.clients = []

		for t in self.transportmodules:
			try:
				self.clients.append(t.Client(serverlocation[t.locationkey],))
				self.logger.info('%s client added' % t.__name__)
			except (ValueError, KeyError):
				self.logger.warning('%s client add failed' % t.__name__)
				pass

		self.serverlocation = serverlocation
		self.logger.info('server location set to to %s' % str(self.serverlocation))
		if len(self.clients) == 0:
			raise TransportError('no client connections possible')

	def __cmp__(self, other):
		return self.serverlocation == other.serverlocation

	# these aren't ordering right, dictionary iteration
	def _send(self, request):
		# Go through all clients until one of them will take the request.
		for client in self.clients:
			try:
				ret = client.send(request)
				return ret
			except TransportError as e:
				# Means this this not the right client. Just need to move on.
				pass
		# It gets here if none of the clients can handle the request.
		if DEBUG:
			print('failed request sending to clients', self.getClientServerLocations(self.clients))
			print('request attr', self.getMultiRequestAttributeName(request))
		msg = '%s' % (request.__class__.__name__,)
		raise TransportError('Error sending request: %s' % msg)

	def getMultiRequestAttributeName(self, request):
		if request.__class__.__name__ in ('MultiRequest','Request'):
			return request.attributename

	def getClientServerLocations(self,clients):
		locations = []
		for c in clients:
			if hasattr(c,'serverlocation'):
				locations.append(c.serverlocation)
		return locations

	def send(self, request):
		result = self._send(request)
		if isinstance(result, Exception):
			raise result
		return result

	def ping(self):
		try:
			self.send(Ping())
		except TransportError:
			return False
		return True

class Server(Base):
	'''
	Basic data transport server. It defines data handler, server location
	and starts it. Can be either local or tcp transport.
	'''
	def __init__(self, dh, logger, tcpport=None):
		Base.__init__(self, logger)
		self.datahandler = dh
		self.servers = {}
		for t in self.transportmodules:
			if tcpport is not None and t is tcptransport:
				args = (self.datahandler, tcpport)
			else:
				args = (self.datahandler,)
			self.servers[t] = t.Server(*args)
			self.servers[t].start()
			self.logger.info('%s server created at location %s'
												% (t.__name__, self.servers[t].location()))

	def exit(self):
		for t in self.transportmodules:
			self.servers[t].exit()
			self.logger.info('%s server exited' % t.__name__)
		self.logger.info('Exited')

	def location(self):
		location = {}
		for t in self.transportmodules:
			location[t.locationkey] = (self.servers[t].location())
		return location

if __name__ == '__main__':
	pass

