#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import data
from databinder import DataBinder
import datatransport
from dbdatakeeper import DBDataKeeper
import event
import leginonobject
import extendedlogging
import threading
import uiserver
import uidata
import gui.wx.Node

import leginonconfig
import os

class ResearchError(Exception):
	pass

class PublishError(Exception):
	pass

class ConfirmationTimeout(Exception):
	pass

class ConfirmationNoBinding(Exception):
	pass

import sys
if sys.platform == 'win32':
	import winsound

def beep():
	try:
		winsound.PlaySound('SystemExclamation', winsound.SND_ALIAS)
		print 'BEEP!'
	except:
		print '\aBEEP!'

class Node(leginonobject.LeginonObject):
	'''Atomic operating unit for performing tasks, creating data and events.'''
	panelclass = None
	eventinputs = [event.Event,
									event.KillEvent,
									event.ConfirmationEvent]

	eventoutputs = [event.PublishEvent,
									event.NodeAvailableEvent,
									event.NodeUnavailableEvent,
									event.NodeInitializedEvent,
									event.NodeUninitializedEvent]

	def __init__(self, name, session, managerlocation=None, otherdatabinder=None, otherdbdatakeeper=None, otheruiserver=None, tcpport=None, xmlrpcport=None, launcher=None, panel=None):
		leginonobject.LeginonObject.__init__(self)
		self.name = name
		self.panel = panel
		
		self.initializeLogger()

		self.managerclient = None

		if session is None or isinstance(session, data.SessionData):
			self.session = session
		else:
			raise TypeError('session must be of proper type')

		self.launcher = launcher

		if otherdatabinder is None:
			self.databinder = DataBinder(self, tcpport=tcpport)
		else:
			self.databinder = otherdatabinder
		if otherdbdatakeeper is None:
			self.dbdatakeeper = DBDataKeeper(loggername=self.logger.name)
		else:
			self.dbdatakeeper = otherdbdatakeeper

		## set up uiserver and uicontainer
		## Either I own the server, or I use the one given to me
		if otheruiserver is None:
			self.uiserver = uiserver.Server(self.name, xmlrpcport, session=session)
			self.uicontainer = self.uiserver
			self.uiserver.getUserPreferencesFromDatabase()
		else:
			self.uiserver = otheruiserver
			self.uicontainer = uidata.LargeContainer(self.name)
			self.uiserver.addObject(self.uicontainer)

		self.confirmationevents = {}
		self.eventswaiting = {}
		self.ewlock = threading.Lock()

		#self.addEventInput(event.Event, self.logEventReceived)
		self.addEventInput(event.KillEvent, self.die)
		self.addEventInput(event.ConfirmationEvent, self.handleConfirmedEvent)
		self.addEventInput(event.SetManagerEvent, self.handleSetManager)

		self.managerlocation = managerlocation
		if managerlocation is not None:
			try:
				self.setManager(self.managerlocation)
			except:
				self.logger.exception('exception in setManager')
				raise

		self.initializeSettings()

	# settings

	def initializeSettings(self):
		if not hasattr(self, 'settingsclass'):
			return
		qsession = data.SessionData(initializer={'user': self.session['user']})
		qdata = self.settingsclass(initializer={'session': qsession,
																						'name': self.name})
		try:
			self.settings = self.research(qdata, results=1)[0]
		except IndexError:
			self.settings = self.settingsclass(initializer=self.defaultsettings)

	def setSettings(self, sd):
		sd['session'] = self.session
		sd['name'] = self.name
		self.publish(sd, database=True, dbforce=True)
		self.settings = sd

	def getSettings(self):
		return self.settings

	def initializeLogger(self, name=None):
		if hasattr(self, 'logger'):
			return
		if name is None:
			name = self.name
		self.logger = extendedlogging.getLogger(name)

	# main, start/stop methods

	def start(self):
		self.onInitialized()
		self.outputEvent(event.NodeInitializedEvent())

	def onInitialized(self):
		if self.panel is None:
			return
		evt = gui.wx.Node.NodeInitializedEvent(self)
		self.panel.GetEventHandler().AddPendingEvent(evt)
		evt.event.wait()

	def setStatus(self, status):
		evt = gui.wx.Node.SetStatusEvent(status)
		self.panel.GetEventHandler().AddPendingEvent(evt)

	def setImage(self, image, statistics={}):
		evt = gui.wx.Node.SetImageEvent(image, statistics)
		self.panel.GetEventHandler().AddPendingEvent(evt)

	def exit(self):
		'''Cleans up the node before it dies.'''
		if self.uicontainer is not None:
			self.uicontainer.delete()
		try:
			self.outputEvent(event.NodeUninitializedEvent(), wait=True,
																										timeout=3.0)
			self.outputEvent(event.NodeUnavailableEvent())
		except (ConfirmationTimeout, IOError):
			pass
		self.delEventInput()
		if self.launcher is not None:
			self.launcher.onDestroyNode(self)
			if self.databinder is self.launcher.databinder:
				return
		self.databinder.exit()

	def die(self, ievent=None):
		'''Tell the node to finish and call exit.'''
		self.exit()
		if ievent is not None:
			self.confirmEvent(ievent)

	# location method
	def location(self):
		location = leginonobject.LeginonObject.location(self)
		if self.launcher is not None:
			location['launcher'] = self.launcher.name
		else:
			location['launcher'] = None
		location['data binder'] = self.databinder.location()
		location['UI'] = self.uiserver.location()
		return location
	# event input/output/blocking methods

	def eventToClient(self, ievent, client, wait=False, timeout=None):
		'''
		base method for sending events to a client
		ievent - event instance
		client - client instance
		wait - True/False, sould confirmation be sent back
		timeout - how long (seconds) to wait for confirmation before
		   raising a ConfirmationTimeout
		'''
		if wait:
			## prepare to wait (but don't wait yet)
			wait_id = ievent.dmid
			ievent['confirm'] = wait_id
			self.ewlock.acquire()
			self.eventswaiting[wait_id] = threading.Event()
			eventwait = self.eventswaiting[wait_id]
			self.ewlock.release()

		### send event and cross your fingers
		try:
			client.push(ievent)
			#self.logEvent(ievent, status='%s eventToClient' % (self.name,))
		except Exception, e:
			# make sure we don't wait for an event that failed
			if wait:
				eventwait.set()
			if not isinstance(e, IOError):
				self.logger.exception('')
			raise

		confirmationevent = None

		if wait:
			### this wait should be released 
			### by handleConfirmedEvent()
			eventwait.wait(timeout)
			notimeout = eventwait.isSet()
			self.ewlock.acquire()
			try:
				confirmationevent = self.confirmationevents[wait_id]
				del self.confirmationevents[wait_id]
				del self.eventswaiting[wait_id]
			except KeyError:
				self.logger.warning('This could be bad to except KeyError')
			self.ewlock.release()
			if not notimeout:
				raise ConfirmationTimeout(str(ievent))
			if confirmationevent['status'] == 'no binding':
				raise ConfirmationNoBinding('%s from %s not bound to any node' % (ievent.__class__.__name__, ievent['node']))

		return confirmationevent

	def outputEvent(self, ievent, wait=False, timeout=None):
		'''output an event to the manager'''
		ievent['node'] = self.name
		if self.managerclient is not None:
			return self.eventToClient(ievent, self.managerclient, wait, timeout)
		else:
			self.logger.warning('No manager, not sending event: %s' % (ievent,))

	def handleConfirmedEvent(self, ievent):
		'''Handler for ConfirmationEvents. Unblocks the call waiting for confirmation of the event generated.'''
		eventid = ievent['eventid']
		status = ievent['status']
		self.ewlock.acquire()
		if eventid in self.eventswaiting:
			self.confirmationevents[eventid] = ievent
			self.eventswaiting[eventid].set()
		self.ewlock.release()
		## this should not confirm ever, right?

	def confirmEvent(self, ievent, status='ok'):
		'''Confirm that an event has been received and/or handled.'''
		if ievent['confirm'] is not None:
			self.outputEvent(event.ConfirmationEvent(eventid=ievent['confirm'], status=status))

	def logEvent(self, ievent, status):
		if not leginonconfig.logevents:
			return
		eventlog = event.EventLog(eventclass=ievent.__class__.__name__, status=status)
		# pubevent is False by default, but just in case that changes
		# we don't want infinite recursion here
		self.publish(eventlog, database=True, pubevent=False)

	def logEventReceived(self, ievent):
		self.logEvent(ievent, 'received by %s' % (self.name,))
		## this should not confirm, this is not the primary handler
		## any event

	def addEventInput(self, eventclass, method):
		'''Map a function (event handler) to be called when the specified event is received.'''
		self.databinder.addBinding(self.name, eventclass, method)

	def delEventInput(self, eventclass=None, method=None):
		'''Unmap all functions (event handlers) to be called when the specified event is received.'''
		self.databinder.delBinding(self.name, eventclass, method)

	# data publish/research methods

	def publish(self, idata, database=False, dbforce=False, pubevent=False, pubeventclass=None, broadcast=False):
		'''
		Make a piece of data available to other nodes.
		Arguments:
			idata - instance of data to publish
			Takes kwargs:
				pubeventclass - PublishEvent subclass to notify with when publishing		
				database - publish to database
		'''
		if database:
			try:
				self.dbdatakeeper.insert(idata, force=dbforce)
			except Exception, e:
				raise
				if isinstance(e, OSError):
					message = str(e)
				elif isinstance(e, IOError):
					message = str(e)
				elif isinstance(e, KeyError):
					message = 'no DBDataKeeper to publish'
				else:
					raise
				raise PublishError(message)

		### publish event
		if pubevent:
			if pubeventclass is None:
				if isinstance(idata, data.DataHandler):
					dataclass = idata.dataclass
				else:
					dataclass = idata.__class__
				try:
					eventclass = event.publish_events[dataclass]
				except KeyError:
					eventclass = None
			else:
				eventclass = pubeventclass
			if eventclass is None:
				raise PublishError('need to know which pubeventclass to use when publishing %s' % (dataclass,))
			e = eventclass()
			e['data'] = idata.reference()
			if broadcast:
				e['destination'] = ''
			return self.outputEvent(e)

	def research(self, datainstance, results=None, readimages=True):
		'''
		find instances in the database that match the 
		given datainstance
		'''
		try:
			resultlist = self.dbdatakeeper.query(datainstance, results, readimages=readimages)
		except Exception, e:
			if isinstance(e, OSError):
				message = str(e)
			elif isinstance(e, IOError):
				message = str(e)
			else:
				raise
			raise ResearchError(message)
		return resultlist

	def researchDBID(self, dataclass, dbid):
		print 'WARNING:  researchDBID() IS TEMPORARY WHILE WE ARE STILL STORING LISTS OF DBIDs'
		return self.dbdatakeeper.direct_query(dataclass, dbid)

	# methods for setting up the manager

	def setManager(self, location):
		'''Set the manager controlling the node and notify said manager this node is available.'''
		self.managerclient = datatransport.Client(location['data binder'])
		available_event = event.NodeAvailableEvent(location=self.location(),
																							nodeclass=self.__class__.__name__)
		self.outputEvent(ievent=available_event, wait=True, timeout=10)

	def handleSetManager(self, ievent):
		'''Event handler calling setManager with event info. See setManager.'''
		## was only resetting self.session if it was previously none
		## now try setting it every time (maybe this would benefit
		## the launcher who could receive this event from different
		## sessions
		self.session = ievent['session']
		## have a new session from manager, so reset session in
		## uiserver and get new user preferences
		self.uiserver.session = self.session
		# this will be ignored if this new session has same user
		# as previous one
		self.uiserver.getUserPreferencesFromDatabase()

		if ievent['session']['name'] == self.session['name']:
			self.setManager(ievent['location'])
		else:
			self.logger.warning('Attempt to set manager rejected')

	# utility methods

	def key2str(self, d):
		'''Makes keys and values into strings.'''
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

	def defineUserInterface(self):
		name = uidata.String('Name', self.name, 'r')
		classstring = uidata.String('Class', self.__class__.__name__, 'r')
		location = self.key2str(self.location())
		locationstruct = uidata.Struct('Location', location, 'r')
		exitmethod = uidata.Method('Exit', self.uiExit)

		# cheat a little here
		clientlogger = extendedlogging.getLogger(self.logger.name + '.'
																							+ datatransport.Client.__name__)
		if clientlogger.container not in self.logger.container.values():
			self.logger.container.addObject(clientlogger.container,
																			position={'span': (1,2), 'expand': 'all'})

		container = uidata.LargeContainer('Node')
		self.uicontainer.addObjects((name, classstring, locationstruct,
																	self.logger.container, exitmethod))

