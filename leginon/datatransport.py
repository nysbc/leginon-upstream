#!/usr/bin/env python

#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import localtransport
import tcptransport
import threading
import extendedlogging
import time
import sys

class Base(object):
	def __init__(self, loggername=None):
		# order matters
		self.transportmodules = [localtransport, tcptransport]
		self.logger = extendedlogging.Logger(self.__class__.__name__, loggername)

class Client(Base):
	# hostname/port -> location or whatever
	# needs to be transport generalized like server
	def __init__(self, serverlocation, loggername=None):
		Base.__init__(self, loggername)

		self.clients = []

		for t in self.transportmodules:
			try:
				self.clients.append(t.Client(serverlocation[t.locationkey],))
				self.logger.info('Added Client from %s' % str(t))
			except (ValueError, KeyError):
				self.logger.info('Failed to add Client from %s' % str(t))
				pass

		self.serverlocation = serverlocation
		self.logger.info('Set Client server location to %s'
														% str(self.serverlocation))
		if len(self.clients) == 0:
			raise IOError('no client connections possible')

		self.lock = threading.RLock()

	# these aren't ordering right, dictionary iteration
	def _pull(self, idata):
		for c in self.clients:
			try:
				newdata = c.pull(idata)
				self.logger.info('Pulled data using Client %s' % str(c))
				return newdata
			except IOError:
				self.logger.info('Failed to pull data using Client %s' % str(c))
				pass
		raise IOError('IOError, unable to pull data ' + str(idata))

	def pull(self, idata):
		self.lock.acquire()
		try:
			ret = self._pull(idata)
			self.lock.release()
			return ret
		except:
			self.lock.release()
			raise

	def _push(self, odata):
		for c in self.clients:
			try:
				ret = c.push(odata)
				self.logger.info('Pushed data using Client %s' % str(c))
				return ret
			except IOError:
				self.logger.info('Failed to push data using Client %s' % str(c))
				pass
			except:
				raise
		raise IOError('IOError, unable to push data ' + str(odata))

	def push(self, odata):
		self.lock.acquire()
		try:
			ret = self._push(odata)
			self.lock.release()
			return ret
		except:
			self.lock.release()
			raise

class Server(Base):
	def __init__(self, dh, tcpport=None, loggername=None):
		Base.__init__(self, loggername)
		self.datahandler = dh
		self.servers = {}
		for t in self.transportmodules:
			if tcpport is not None and t is tcptransport:
				args = (self.datahandler, tcpport)
			else:
				args = (self.datahandler,)
			self.servers[t] = t.Server(*args)
			self.servers[t].start()
			self.logger.info('Created server type %s at %s'
												% (t, self.servers[t].location()))

	def exit(self):
		for t in self.transportmodules:
			self.servers[t].exit()
			self.logger.info('Server type %s exited' % t)
		self.datahandler.exit()
		self.logger.info('Data handler exited')

	def location(self):
		location = {}
		for t in self.transportmodules:
			location[t.locationkey] = (self.servers[t].location())
		return location

if __name__ == '__main__':
	pass

