#
# COPYRIGHT:
#       The Leginon software is Copyright under
#       Apache License, Version 2.0
#       For terms of the license agreement
#       see  http://leginon.org
#
import socketserver
import socket
from leginon import socketstreamtransport
import errno
from pyami import mysocket

locationkey = 'TCP transport'

class TransportError(socketstreamtransport.TransportError):
	pass

class Server(socketstreamtransport.Server, socketserver.ThreadingTCPServer):
	#allow_reuse_address = True
	def __init__(self, dh, port=None):
		socketstreamtransport.Server.__init__(self, dh)

		# instantiater can choose a port or we'll choose one for them
		if port is not None:
			try:
				socketserver.ThreadingTCPServer.__init__(self, ('', port),
																									socketstreamtransport.Handler)
			except socket.error as e:
				raise TransportError(e)
		else:
			exception = True
			# range define by IANA as dynamic/private or so says Jim
			portrange = (49152, 65536)
			port = portrange[0]
			while port <= portrange[1]:
				try:
					socketserver.ThreadingTCPServer.__init__(self, ('', port),
																									socketstreamtransport.Handler)
					exception = False
					break
				except socket.error as e:
					if hasattr(e, 'errno'):
						en = e.errno
						if en == errno.EADDRINUSE:
							port += 1
							continue
						else:
							raise TransportError(e)
					else:
						raise TransportError(e)
			if exception:
				string = 'No ports in range %s available' % (portrange,)
				raise TransportError(string)
		self.request_queue_size = 15
		self.port = port

	def location(self):
		location = socketstreamtransport.Server.location(self)
		location['hostname'] = mysocket.gethostname().lower()
		location['port'] = self.port
		return location

	def exit(self):
		socketstreamtransport.Server.exit(self)
		self.server_close()

class Client(socketstreamtransport.Client):
	def __init__(self, location):
		socketstreamtransport.Client.__init__(self, location)

	def connect(self, family=socket.AF_INET, type=socket.SOCK_STREAM):
		s = socket.socket(family, type)
		try:
			hostname = self.serverlocation['hostname']
			port = self.serverlocation['port']
		except KeyError:
			raise TransportErrorr('invalid location')
		try:
			s.connect((hostname, port))
		except socket.error as e:
			raise TransportError(e)
		return s

Server.clientclass = Client
Client.serverclass = Server

