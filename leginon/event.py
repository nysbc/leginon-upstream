## defines the Event and EventHandler classes

import leginonobject
import data

class Event(data.Data):
	def __init__(self, content=None):
		data.Data.__init__(self, content)


## Standard Event Types:
##
##	Event
##		NotificationEvent
##			NodeAvailableEvent
##				LauncherAvailableEvent
##			NodeUnavailableEvent
##			PublishEvent
##			UnpublishEvent
##			ListPublishEvent
##		ControlEvent
##			StartEvent
##			Stopvent
##			NumericControlEvent
##			LaunchEvent

### generated by a node to notify manager that node is ready
class NotificationEvent(Event):
	'Event sent by a node to the manager to indicate a successful init'
	def __init__(self, content):
		Event.__init__(self, content)

class NodeAvailableEvent(NotificationEvent):
	'Event sent by a node to the manager to indicate a successful init'
	def __init__(self):
		NotificationEvent.__init__(self, content=None)

class LauncherAvailableEvent(NodeAvailableEvent):
	'Event sent by a node to the manager to indicate a successful init'
	def __init__(self):
		NodeAvailableEvent.__init__(self)

class PublishEvent(NotificationEvent):
	'Event indicating data was published'
	def __init__(self, dataid):
		NotificationEvent.__init__(self, content=dataid)

class UnpublishEvent(NotificationEvent):
	'Event indicating data was unpublished (deleted)'
	def __init__(self, dataid):
		NotificationEvent.__init__(self, content=dataid)

class PublishImageEvent(NotificationEvent):
	'Event indicating image was published'
	def __init__(self, dataid):
		NotificationEvent.__init__(self, content=dataid)

# this could be a subclass of publish event, but I'm not sure if that
# would confuse those not looking for a list
class ListPublishEvent(Event):
	'Event indicating data was published'
	def __init__(self, idlist):
		if type(idlist) == list:
			Event.__init__(self, content = idlist)
		else:
			raise TypeError

class ControlEvent(Event):
	'Event that passes a value with it'
	def __init__(self, content=None):
		Event.__init__(self, content)

class StartEvent(ControlEvent):
	'Event that signals a start'
	def __init__(self):
		ControlEvent.__init__(self)
	
class StopEvent(ControlEvent):
	'Event that signals a stop'
	def __init__(self):
		ControlEvent.__init__(self)

class NumericControlEvent(ControlEvent):
	'ControlEvent that allows only numeric values to be passed'
	def __init__(self, content):
		allowedtypes = (int, long, float)
		if type(content) in allowedtypes:
			ControlEvent.__init__(self, content)
		else:
			raise TypeError('NumericControlEvent content type must be in %s' % allowedtypes)

class LaunchEvent(ControlEvent):
	'ControlEvent sent to a NodeLauncher specifying a node to launch'
	#def __init__(self, nodeid, nodeclass, newproc=0):
	def __init__(self, newproc, targetclass, args=(), kwargs={}):
		nodeinfo = {'newproc':newproc,'targetclass':targetclass, 'args':args, 'kwargs':kwargs}
		Event.__init__(self, content=nodeinfo)

###########################################################
## event related exceptions

class InvalidEventError(TypeError):
	pass

