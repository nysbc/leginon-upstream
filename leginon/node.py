import threading
import code
import leginonobject
import event
import datatransport
import datahandler
import dbdatakeeper
import interface
import sys
import copy
import time

# False is not defined in early python 2.2
False = 0
True = 1

if sys.platform == 'win32':
	sys.coinit_flags = 0

class DataHandler(leginonobject.LeginonObject):
	'''
	handles data published by the node
	'''
	def __init__(self, id, session, mynode):
		leginonobject.LeginonObject.__init__(self, id, session)
		## giving these all the same id, don't know why
		self.datakeeper = datahandler.SimpleDataKeeper(id, session)
		self.databinder = datahandler.DataBinder(id, session)
		self.dbdatakeeper = dbdatakeeper.DBDataKeeper(id, session)
		self.node = mynode

	def local_only_insert(self, idata):
		'''Insert data into the datahandler. Only events can be inserted from and external source. Events are bound. See setBinding.'''
		if isinstance(idata, event.Event):
			self.databinder.insert(idata)
		else:
			if idata['id'][:-1] == self.id[:-1]:
				self.datakeeper.insert(copy.deepcopy(idata))
			else:
				raise RuntimeError('local only insert on data not from this node')

	def insert(self, idata):
		if isinstance(idata, event.Event):
			self.databinder.insert(idata)
		else:
			self.datakeeper.insert(copy.deepcopy(idata))

	def query(self, id):
		return self.datakeeper.query(id)

	def setBinding(self, eventclass, func):
		'''Overides datahandler.DataBinder, making sure it binds Event type only.'''
		if issubclass(eventclass, event.Event):
			self.databinder.setBinding(eventclass, func)
		else:
			raise event.InvalidEventError('eventclass must be Event subclass')

	def dbInsert(self, idata):
		self.dbdatakeeper.insert(idata)

	def dbQuery(self, idata, results=None):
		self.dbdatakeeper.query(idata, results)

	def __getattr__(self, attr):
		return getattr(self.datakeeper, attr)


class Node(leginonobject.LeginonObject):
	'''Atomic operating unit for performing tasks, creating data and events.'''
	def __init__(self, id, session, nodelocations = {}, datahandler=DataHandler, tcpport=None, xmlrpcport=None, clientclass = datatransport.Client, launchlock=None):
		leginonobject.LeginonObject.__init__(self, id, session)

		self.nodelocations = nodelocations
		self.launchlock = launchlock

		self.eventmapping = {'outputs':[], 'inputs':[]}

		self.datahandler = datahandler(self.ID(), session, self)

		self.server = datatransport.Server(self.ID(),
																	self.datahandler, tcpport)
		self.clientclass = clientclass

		self.uiserver = interface.Server(self.ID(), xmlrpcport)

		self.confirmwaitlist = {}

		self.addEventOutput(event.PublishEvent)
		self.addEventOutput(event.UnpublishEvent)
		self.addEventOutput(event.NodeAvailableEvent)
		self.addEventOutput(event.NodeUnavailableEvent)
		self.addEventOutput(event.NodeInitializedEvent)
		self.addEventOutput(event.NodeUninitializedEvent)

		self.addEventInput(event.Event, self.logEventReceived)
		self.addEventInput(event.KillEvent, self.die)
		self.addEventInput(event.ConfirmationEvent, self.handleConfirmedEvent)
		self.addEventInput(event.NodeAvailableEvent, self.handleAddNode)

		if 'manager' in self.nodelocations:
			try:
				self.addManager(self.nodelocations['manager'])
			except:
				self.printerror('exception in addManager')
				raise
			else:
				self.printerror('connected to manager')
		self.die_event = threading.Event()

	def releaseLauncher(self):
		## release the launch lock
		if self.launchlock is not None:
			print self, 'releasing launchlock'
			self.launchlock.release()

	# main, start/stop methods

	def main(self):
		'''The body of taking place when the node is started. See start.'''
		pass

	def exit(self):
		'''Cleans up the node before it dies.'''
		self.outputEvent(event.NodeUnavailableEvent(self.ID()))
		self.server.exit()
		self.printerror('exited')

	def die(self, ievent=None):
		'''Tell the node to finish and call exit.'''
		self.die_event.set()

	def start(self):
		'''Call to make the node active and react to a call to exit. Calls main.'''
		#interact_thread = self.interact()

		self.releaseLauncher()
		self.outputEvent(event.NodeInitializedEvent(self.ID()))
		self.main()

		# wait until the interact thread terminates
		#interact_thread.join()
		self.die_event.wait()
		self.outputEvent(event.NodeUninitializedEvent(self.ID()))
		self.exit()

	# location method

	def location(self):
		loc = leginonobject.LeginonObject.location(self)
		loc.update(self.server.location())
		loc['UI port'] = self.uiserver.port
		return loc

	# event input/output/blocking methods

	def outputEvent(self, ievent, wait=0):
		'''Send the event to the manager to be routed where necessary.'''
		eventstatus = '%s to manager' % (self.id,)
		self.logEvent(ievent, status=eventstatus)
		try:
			ievent['confirm'] = True
			self.managerclient.push(ievent)
		except KeyError:
			self.printerror('cannot output event %s' % ievent)
			return
		if wait:
			self.waitEvent(ievent)

	def logEvent(self, ievent, status):
		eventlog = event.EventLog(self.ID(), eventclass=ievent.__class__.__name__, status=status)
		## pubevent is False by default, but just in case that changes
		## we don't want infinite recursion here
		self.publish(eventlog, database=True, pubevent=False)

	def logEventReceived(self, ievent):
		self.logEvent(ievent, 'received by %s' % (self.id,))

	def addEventInput(self, eventclass, func):
		'''Map a function (event handler) to be called when the specified event is received.'''
		## simplified this, but is there a reason for the original
		#self.server.datahandler.setBinding(eventclass, func)
		self.datahandler.setBinding(eventclass, func)
		if eventclass not in self.eventmapping['inputs']:
			self.eventmapping['inputs'].append(eventclass)

	def delEventInput(self, eventclass):
		'''Unmap all functions (event handlers) to be called when the specified event is received.'''
		## simplified this, but is there a reason for the original
		#self.server.datahandler.setBinding(eventclass, None)
		self.datahandler.setBinding(eventclass, None)
		if eventclass in self.eventmapping['inputs']:
			self.eventmapping['inputs'].remove(eventclass)

	def addEventOutput(self, eventclass):
		'''Register the ability for the node to output specified event.'''
		if eventclass not in self.eventmapping['outputs']:
			self.eventmapping['outputs'].append(eventclass)
		
	def delEventOutput(self, eventclass):
		'''Unregister the ability for the node to output specified event.'''
		if eventclass in self.eventmapping['outputs']:
			self.eventmapping['outputs'].remove(eventclass)

	def confirmEvent(self, ievent):
		'''Confirm that an event has been received and/or handled.'''
		#self.outputEvent(event.ConfirmationEvent(self.ID(), ievent.id))
		self.outputEvent(event.ConfirmationEvent(self.ID(), eventid=ievent['id']))

	def waitEvent(self, ievent):
		'''Block for confirmation of a generated event.'''
		#if not ievent.id in self.confirmwaitlist:
		#	self.confirmwaitlist[ievent.id] = threading.Event()
		#self.confirmwaitlist[ievent.id].wait()
		if not ievent['id'] in self.confirmwaitlist:
			self.confirmwaitlist[ievent['id']] = threading.Event()
		self.confirmwaitlist[ievent['id']].wait()

	def handleConfirmedEvent(self, ievent):
		'''Handler for ConfirmationEvents. Unblocks the call waiting for confirmation of the event generated.'''
		# this is bad since it will fill up with lots of events
		eventid = ievent['eventid']
		if not eventid in self.confirmwaitlist:
			self.confirmwaitlist[eventid] = threading.Event()
		self.confirmwaitlist[eventid].set()

		#del self.confirmwaitlist[eventid]

	# data publish/research methods

	def publish(self, idata, **kwargs):
		'''
		Make a piece of data available to other nodes.
		Arguments:
			idata - instance of data to publish
			Takes kwargs:
				eventclass - PublishEvent subclass to notify with when publishing		
				confirm - Wait until Event is confirmed to return
				database - publish to database
				remote - publish to another node's datahandler (may be changed)
		'''
		if 'remote' in kwargs and kwargs['remote']:
			self.publishRemote(idata)
			return

		if 'database' in kwargs and kwargs['database']:
			try:
				idata['session'] = self.session
				self.datahandler.dbInsert(idata)
			except KeyError:
				self.printerror('no DBDataKeeper to publish: %s' % str(idata['id']))

		self.datahandler.insert(idata)

		### publish event
		if 'pubevent' in kwargs and kwargs['pubevent']:
			if 'confirm' in kwargs:
				confirm = kwargs['confirm']
			else:
				confirm = False
			eventclass = event.publish_events[idata.__class__]
			e = eventclass(self.ID(), dataid=idata['id'], confirm=confirm)
			self.outputEvent(e)

	def research(self, dataclass=None, datainstance=None, **kwargs):
		'''
		How a node finds some data in the leginon system:
			1) Using a data class and keyword args:
				self.research(dataclass=myclass, stuff=4)
			2) Using a partially filled data instance:
				self.research(datainstance=mydata)

			In both cases, zero or more results (data instances)
			will be returned in a list.  The result list will
			not contain two instaces with the same ID.
		'''

		#### make some sense out of args
		### for research by dataclass, use kwargs to find instance
		if dataclass is not None:
			pass


		results = []

		### standard search for data by ID
		if 'id' in kwargs and 'session' in kwargs and len(kwargs) == 2:
			if self.session == kwargs['session']:
				try:
					result.append(self.researchByDataID(kwargs['id']))
				except ResearchError:
					pass

		### DBDataKeeper query
		if results == 0 or results > len(result):
			try:
				datainstance = kwargs['dataclass'](('dummy ID',))
				# copy should suffice
				indices = copy.copy(kwargs)
				del indices['dataclass']
				for index in indices:
					if index not in datainstance:
						raise ValueError
			except ValueError:
				self.printerror('DBDataKeeper research failed, bad kwarg \'%s\'' % index)
			else:
				try:
					result += self.datahandler.dbQuery(datainstance, indices, results - len(result))
				except Exception, e: 
					if isinstance(e, KeyError):
						self.printerror('DBDataKeeper research failed, no DBDataKeeper')
					else:
						self.printerror('DBDataKeeper research failed, %s' % str(e))

		return result

	def unpublish(self, dataid, eventclass=event.UnpublishEvent):
		'''Make a piece of data unavailable to other nodes.'''
		if not issubclass(eventclass, event.UnpublishEvent):
			raise TypeError('UnpublishEvent subclass required')
		self.datahandler.remove(dataid)
		self.outputEvent(eventclass(self.ID(), dataid=dataid))

	def publishRemote(self, idata):
		'''Publish a piece of data with the specified data ID, setting all other data with the same data ID to the data value (including other nodes).'''
		dataid = idata['id']
		nodeiddata = self.researchByLocation(self.nodelocations['manager'], dataid)
		if nodeiddata is None:
			# try a partial ID lookup
			nodeiddata = self.researchByLocation(self.nodelocations['manager'], dataid[:1])

		if nodeiddata is None:
			raise PublishError('No such Data ID: %s' % (dataid,))

		for nodeid in nodeiddata['location']:
			nodelocation = self.researchByLocation(self.nodelocations['manager'], nodeid)
			client = self.clientclass(self.ID(), nodelocation['location'])
			client.push(idata)

	def locateDataByID(self, dataid):
		'''
		Asks manager to find nodes that are keeping data
		Returns a list of locations
		'''
		pass

	def researchByLocation(self, loc, dataid):
		'''Get a piece of data with the specified data ID by the location of a node.'''
		client = self.clientclass(self.ID(), loc)
		cdata = client.pull(dataid)
		return cdata

	def researchByDataID(self, dataid):
		'''Get a piece of data with the specified data ID. Currently retrieves the data from the last node to publish it.'''
		nodeiddata = self.managerclient.pull(dataid)

		if nodeiddata is None:
			raise ResearchError('No such data ID: %s' % (dataid,))

		# should interate over nodes, be crafty, etc.
		datalocationdata = self.managerclient.pull(nodeiddata['location'][-1])
		newdata = self.researchByLocation(datalocationdata['location'], dataid)
		return newdata

	# methods for setting up the manager

	def addManager(self, loc):
		'''Set the manager controlling the node and notify said manager this node is available.'''
		self.managerclient = self.clientclass(self.ID(), loc)
		available_event = event.NodeAvailableEvent(self.ID(), location=self.location(),
												nodeclass=self.__class__.__name__)
		self.outputEvent(ievent=available_event, wait=True)

	def handleAddNode(self, ievent):
		'''Event handler calling adddManager with event info. See addManager.'''
		if ievent['nodeclass'] == 'Manager':
			self.addManager(ievent['location'])

	# utility methods

	def interact(self):
		'''Create a prompt with namespace within the class instance for command linecontrol of the node.'''
		banner = "Starting interpreter for %s" % self.__class__
		readfunc = self.raw_input
		local = locals()
		t = threading.Thread(name='interact thread', target=code.interact,
													args=(banner, readfunc, local))
		t.setDaemon(1)
		t.start()
		return t

	def raw_input(self, prompt):
		'''Helper function for interact. See interact.'''
		newprompt = '%s%s' % (str(self.id), prompt)
		return raw_input(newprompt)

	# UI methods

	def registerUIMethod(self, func, name, argspec, returnspec=None):
		'''Register a method with the UI server by function specifying argument and return value specifications.'''
		return self.uiserver.registerMethod(func, name, argspec, returnspec)

	def registerUIData(self, name, xmlrpctype, permissions=None,
					choices=None, default=None, pyname=None, callback=None, subtype=None):
		'''Register a data value with the UI server.'''
		return self.uiserver.registerData(name, xmlrpctype, permissions,
																		choices, default, pyname, callback, subtype)

	def registerUIContainer(self, name=None, content=()):
		'''Register a container for data and methods with the UI server.'''
		return self.uiserver.registerContainer(name, content)

	def registerUISpec(self, name=None, content=()):
		'''Register the entire UI specification with the UI server.'''
		return self.uiserver.registerSpec(name, content)

	def uiDataDict(self, value=None):
		'''Generate a dictionary of currently published data and attributes in a XML-RPC compatible format.'''
		if value is None:
			try:
				return self.key2str(self.datahandler.datadict)
			except AttributeError:
				return {}

	def key2str(self, d):
		'''Helper function for uiDataDict. Makes keys and values into strings. See uiDataDict.'''
		if type(d) is dict:
			newdict = {}
			for k in d:
				newdict[str(k)] = self.key2str(d[k])
			return newdict
		else:
			return str(d)

	def uiExit(self):
		'''UI function calling die. See die.'''
		self.die()
		return ''

	def defineUserInterface(self):
		'''
		This is where you register methods that can be accessed
		by a user interface through XML-RPC
		To register a method use:
		   self.registerUIFunction(self.meth, argspec [,alias])
		argspec should be a sequence object like this example:
		(
		  {'name':'mynum', 'alias':MyNum','type':'integer', 'default':1},
		  {'name':'mystr', 'alias':'MyStr', 'type':'string', 'default':'hello'},
		  {'name':'selection', 'alias':'Selection', 'type':('red','green','blue')}
		)
		- name is currently ignored and therefore argspec must be
		  properly ordered for positional arguments
		- arg types are found in interface.xmlrpctypes and this 
		  can also be set to sequence for an enumeration type.
		- alias is the alias that should be used by the UI
		  (defaults to __name__)
		'''

		exitspec = self.registerUIMethod(self.uiExit, 'Exit', ())

		idspec = self.registerUIData('ID', 'array', 'r', default=self.id)
		classspec = self.registerUIData('Class', 'string', 'r',
																		default=self.__class__.__name__)
		locationspec = self.registerUIData('Location', 'struct', 'r',
																	default=self.location())

		datatree = self.registerUIData('Data', 'struct', permissions='r', callback=self.uiDataDict)

		cont = self.registerUIContainer('Node', (exitspec, idspec, classspec, locationspec, datatree))

		myspec = self.registerUISpec('Node',
								(cont,))

		return myspec


class ResearchError(Exception):
	pass

class PublishError(Exception):
	pass
