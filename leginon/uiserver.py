#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#
import socket
import threading
import uidata
import extendedxmlrpclib
import Queue
import data
import xmlrpc
import dbdatakeeper

# preferences
import cPickle
#import leginonconfig
#import os

class NoValueError(Exception):
	pass

userprefs = {'prefs': {}, 'user': None}

class Server(xmlrpc.Server, uidata.Container):
	typelist = uidata.Container.typelist + ('server',)
	def __init__(self, name='UI', port=None, tries=5,
								session=None):
		self.xmlrpcclients = []
		self.localclients = []
		self.tries = tries
		self.dbdatakeeper = dbdatakeeper.DBDataKeeper()
		self.session = session

		self.pref_lock = threading.Lock()

		xmlrpc.Server.__init__(self, port=port)

		uidata.Container.__init__(self, name)
		self.server = self

		self.xmlrpcserver.register_function(self.setFromClient, 'set')
		self.xmlrpcserver.register_function(self.commandFromClient, 'command')
		self.xmlrpcserver.register_function(self.addXMLRPCClientServer,	
																				'add client')

	def __str__(self):
		return object.__str__(self)

	def __repr__(self):
		return object.__repr__(self)

	def location(self):
		location = {}
		location['hostname'] = self.hostname
		location['XML-RPC port'] = self.port
		location['instance'] = self
		return location

	def _getNameList(self):
		return []

	def _getObjectFromList(self, namelist):
		namelist[0] = self.name
		return uidata.Container._getObjectFromList(self, namelist)

	def setFromClient(self, namelist, value):
		'''this is how a UI client sets a data value'''
		uidataobject = self._getObjectFromList(namelist)
		if not isinstance(uidataobject, uidata.Data):
			raise TypeError('name list does not resolve to Data instance')
		# except from this client?
		uidataobject._set(value)

		# record new value in a pickle
		if uidataobject.persist:
			self.setDatabaseFromObject(uidataobject)

		return ''

	def commandFromClient(self, namelist, args):
		uimethodobject = self._getObjectFromList(namelist)
		if not isinstance(uimethodobject, uidata.Method):
			raise TypeError('name list does not resolve to Method instance')
		apply(uimethodobject.method, args)
		return ''

	def addXMLRPCClientServer(self, hostname, port):
		for client in list(self.xmlrpcclients):
			if client.serverhostname == hostname and client.serverport == port:
				self.xmlrpcclients.remove(client)
			
		client = xmlrpc.Client(hostname, port)
		self.xmlrpcclients.append(client)
		for childobject in self.values():
			self._addObject(childobject, client)
		return ''

	def addLocalClient(self, client):
		self.localclients.append(client)
		for childobject in self.values():
			self._addObject(childobject, client)

	def localExecute(self, commandstring, properties,
										client=None, block=True, thread=False):
		if client in self.localclients:
			localclients = [client]
		elif client is None:
			localclients = self.localclients
		else:
			return
		for localclient in localclients:
			target = getattr(localclient, commandstring)
			args = (properties,)
			if thread:
				localthread = threading.Thread(name='UI local execute thread',
																				target=target, args=args)
				localthread.start()
			else:
				apply(target, args)

	def XMLRPCExecute(self, commandstring, properties,
										client=None, block=True, thread=False):
		if client in self.xmlrpcclients:
			xmlrpcclients = [client]
		elif client is None:
			xmlrpcclients = self.xmlrpcclients
		else:
			return

		removeclients = []
		if thread:
			removeclientslock = threading.Lock()
		else:
			removeclientslock = None

		# marshalling XML-RPC data for each client inefficient
		for client in xmlrpcclients:
			if thread:
				xmlrpcthread = threading.Thread(name='UI XML-RPC execute thread',
																				target=self.XMLRPCClientExecute,
																				args=(commandstring, properties, client,
																							removeclients, removeclientslock))
				xmlrpcthread.start()
			else:
				self.XMLRPCClientExecute(commandstring, properties, client,
																	removeclients, removeclientslock)

		for removeclient in removeclients:
			try:
				self.xmlrpcclients.remove(removeclient)
			except ValueError:
				pass

	def XMLRPCClientExecute(self, commandstring, properties, client,
													removeclients=None, removeclientslock=None):
		failures = 0
		while failures < self.tries:
			try:
				client.execute(commandstring, (properties,))
				return
			except (extendedxmlrpclib.ProtocolError, socket.error), e:
				failures += 1
		if removeclientslock is not None:
			removeclientslock.acquire()
		removeclients.append(client)
		if removeclientslock is not None:
			removeclientslock.release()

#	def addObject(self, uiobject, block=True, thread=False):
#		uidata.Container.addObject(self, uiobject, block, thread)
#		self.usePreferences()

	def propertiesFromObject(self, uiobject, block, thread):
		properties = {}
		properties['dependencies'] = []
		properties['namelist'] = uiobject._getNameList()
		properties['typelist'] = uiobject.typelist
		try:
			properties['value'] = uiobject.value
		except AttributeError:
			properties['value'] = None
		properties['configuration'] = uiobject.configuration
		if thread:
			block = False
		properties['block'] = block
		properties['position'] = uiobject.parent.positions[uiobject.name]
		if isinstance(uiobject, uidata.Container):
			properties['children'] = []
			for childobject in uiobject.values():
				properties['children'].append(self.propertiesFromObject(childobject,
																																block, thread))
		return properties

	def _addObject(self, uiobject, client=None, block=True, thread=True):
		if client is None:
			flag = self.setObjectFromDatabase(uiobject)
		properties = self.propertiesFromObject(uiobject, block, thread)
		self.localExecute('addFromServer', properties, client, block, thread)
		self.XMLRPCExecute('add', properties, client, block, thread)

	def _setObject(self, uiobject, client=None, block=True, thread=False,
									database=False):
		properties = {}
		properties['namelist'] = uiobject._getNameList()
		properties['value'] = uiobject.value
		if database:
			self.setDatabaseFromObject(uiobject)

		if thread:
			block = False
		properties['block'] = block

		self.localExecute('setFromServer', properties, client, block, thread)
		self.XMLRPCExecute('set', properties, client, block, thread)

	def _deleteObject(self, uiobject, client=None, block=True, thread=False):
		properties = {}
		properties['namelist'] = uiobject._getNameList()

		if thread:
			block = False
		properties['block'] = block

		self.localExecute('removeFromServer', properties, client, block, thread)
		self.XMLRPCExecute('remove', properties, client, block, thread)

	def _configureObject(self, uiobject, client=None, block=True, thread=False):
		properties = {}
		properties['namelist'] = uiobject._getNameList()
		properties['configuration'] = uiobject.configuration

		if thread:
			block = False
		properties['block'] = block

		self.localExecute('configureFromServer', properties, client, block, thread)
		self.XMLRPCExecute('configure', properties, client, block, thread)

	# file based preference methods

	def getUserPreferencesFromDatabase(self):
		'''
		get current user's prefs from DB and put them in 
		userprefs
		'''
		if self.session is None:
			return
		## check if same user
		if userprefs['prefs'] and self.session['user'].dbid == userprefs['user']:
				return
		userdbid = self.session['user'].dbid
		print 'Loading user preferences (uid: %s)...' % (userdbid,)
		userprefs['user'] = userdbid
		sessionquery = data.SessionData(user=self.session['user'])
		prefquery = data.UIData(session=sessionquery)
		results = self.dbdatakeeper.query(prefquery)
		## results are ordered by newest stuff first
		## so now get the newest stuff into a dict
		for result in results:
			value = result['value']
			## check if this was from a previous version
			if value.o is None:
				continue
			key = tuple(result['object'])
			if key not in userprefs['prefs']:
				userprefs['prefs'][key] = result['value']
		print 'Done loading preferences.'

	def setObjectFromDatabase(self, uiobject):
		if self.dbdatakeeper is None or self.session is None:
			return False
		if isinstance(uiobject, uidata.Container):
			for childobject in uiobject.values():
				self.setObjectFromDatabase(childobject)
		if not isinstance(uiobject, uidata.Data) or not uiobject.persist:
			return False
		namelist = tuple(uiobject._getNameList())
		try:
			try:
				value = userprefs['prefs'][namelist]
			except KeyError:
				return False
			### get object from Object
			if value is not None:
				value = value.o
			uiobject.set(value, server=False)
			return True
		except:
			print 'Error setting preference'
			raise
			return False

	def setDatabaseFromObject(self, uiobject):
		if self.dbdatakeeper is None:
			print 'Cannot save UI values to database without dbdatakeeper'
			return
		if self.session is None:
			print 'Cannot save UI values to database without session'
			return
		if isinstance(uiobject, uidata.Container):
			for childobject in uiobject.values():
				self.setDatabaseFromObject(childobject)
		if not isinstance(uiobject, uidata.Data):
			return
		namelist = uiobject._getNameList()
		value = uiobject.get()
		initializer = {'session': self.session,
										'object': namelist,
										'value': value}
		odata = data.UIData(initializer=initializer)
		self.dbdatakeeper.insert(odata, force=True)

	def _setObjectFromFile(self, uiobject, d):
		if isinstance(uiobject, uidata.Container):
			for childobject in uiobject.values():
				self._setObjectFromFile(childobject, d)
		if not isinstance(uiobject, uidata.Data) or not uiobject.persist:
			return
		namelist = uiobject._getNameList()
		if tuple(namelist) in d:
			try:
				uiobject.set(d[tuple(namelist)], server=False)
			except:
				print 'Error setting preference'

	def setObjectFromFile(self, uiobject):
		try:
			f = file(leginonconfig.PREFS_FILE, 'rb')
		except IOError, e:
			print 'Error setting preferences', e.strerror
			return
		try:
			d = cPickle.load(f)
		except Exception, e:
			print 'Invalid file for preferences'
			f.close()
			return
		self._setObjectFromFile(uiobject, d)
		f.close()
	
	def setFileFromObject(self, uiobject):
		if not isinstance(uiobject, uidata.Data):
			return
		try:
			f = file(leginonconfig.PREFS_FILE, 'wb')
		except IOError, e:
			print 'Error saving preferences', e.strerror
			return
		try:
			d = cPickle.load(f)
		except:
			d = {}
		namelist = uiobject._getNameList()
		d[tuple(namelist)]= uiobject.get()
		cPickle.dump(d, f, cPickle.HIGHEST_PROTOCOL)
		f.close()

	def setFromPickle(self, namelist, value):
		uidataobject = self._getObjectFromList(namelist)
		if not isinstance(uidataobject, uidata.Data):
			raise TypeError('name list does not resolve to Data instance')
		uidataobject._set(value, usercallback=False)

	def usePreferences(self):
		d = self.getPickle()
		if not d:
			return
		for key, value in d.items():
			namelist = list(key)
			try:
				self.setFromPickle(namelist, value)
			except ValueError:
				pass

	def getPickle(self, namelist=None):
		self.pref_lock.acquire()
		try:
			value = self._getPickle(namelist)
		finally:
			self.pref_lock.release()
		return value

	def _getPickle(self, namelist=None):
		fname = '%s.pref' % (self.name,)
		fname = os.path.join(leginonconfig.PREFS_PATH, fname)
		try:
			f = file(fname, 'rb')
		except IOError:
			d = {}
		else:
			try:
				d = cPickle.load(f)
			except:
				print 'bad pickle in %s' % (fname,)
				d = {}
			f.close()
		if namelist is None:
			value = d
		else:
			try:
				value = d[tuple(namelist)]
			except KeyError:
				value = None
		return value

	def updatePickle(self, namelist, value):
		self.pref_lock.acquire()
		try:
			self._updatePickle(namelist, value)
		finally:
			self.pref_lock.release()

	def _updatePickle(self, namelist, value):
		### maybe want a lock on this
		fname = '%s.pref' % (self.name,)
		fname = os.path.join(leginonconfig.PREFS_PATH, fname)

		## read current value
		try:
			f = file(fname, 'rb')
		except IOError:
			d = {}
		else:
			try:
				d = cPickle.load(f)
			except:
				print 'bad pickle in %s' % (fname,)
				d = {}
			f.close()
		## update and store
		d[tuple(namelist)] = value
		f = file(fname, 'wb')
		cPickle.dump(d, f, cPickle.HIGHEST_PROTOCOL)
		f.close()

