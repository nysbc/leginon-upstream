# The Leginon software is Copyright 2004
# The Scripps Research Institute, La Jolla, CA
# For terms of the license agreement
# see http://ami.scripps.edu/software/leginon-license
#
# $Source: /ami/sw/cvsroot/pyleginon/gui/wx/Events.py,v $
# $Revision: 1.19 $
# $Name: not supported by cvs2svn $
# $Date: 2005-02-28 22:17:52 $
# $Author: suloway $
# $State: Exp $
# $Locker:  $

import wx

class FactoryEvent(wx.PyEvent):
	_eventtype = None
	def __init__(self):
		wx.PyEvent.__init__(self)
		self.SetEventType(self._eventtype)

def eventFactory(name):
	toks = name.split()
	basename = ''
	bindername = ''
	for tok in toks:
		basename += tok
		bindername += tok.upper() + '_'
	eventname = basename + 'Event'
	typename = eventname + 'Type'
	bindername = 'EVT_' + bindername[:-1]
	g = globals()
	g[typename] = wx.NewEventType()
	g[bindername] = wx.PyEventBinder(g[typename])
	g[eventname] = type(eventname, (FactoryEvent,), {'_eventtype': g[typename]})

eventFactory('Acquisition Done')
eventFactory('Atlas Calculated')
eventFactory('Atlas Published')
eventFactory('Calibration Done')
eventFactory('Get Instrument Done')
eventFactory('Set Instrument Done')
eventFactory('Measurement Done')
eventFactory('Submit Targets')
eventFactory('Targets Submitted')
eventFactory('Manual Updated')
eventFactory('Update Drawing')
eventFactory('Found Targets')
eventFactory('Get Atlases Done')
eventFactory('Set Atlas Done')

PlayerEventType = wx.NewEventType()
SetImageEventType = wx.NewEventType()
SetTargetsEventType = wx.NewEventType()
StatusUpdatedEventType = wx.NewEventType()
SetTEMEventType = wx.NewEventType()
SetTEMsEventType = wx.NewEventType()
SetCCDCameraEventType = wx.NewEventType()
SetCCDCamerasEventType = wx.NewEventType()
TEMChangeEventType = wx.NewEventType()
CCDCameraChangeEventType = wx.NewEventType()

EVT_PLAYER = wx.PyEventBinder(PlayerEventType)
EVT_SET_IMAGE = wx.PyEventBinder(SetImageEventType)
EVT_SET_TARGETS = wx.PyEventBinder(SetTargetsEventType)
EVT_STATUS_UPDATED = wx.PyEventBinder(StatusUpdatedEventType)
EVT_SET_TEM = wx.PyEventBinder(SetTEMEventType)
EVT_SET_TEMS = wx.PyEventBinder(SetTEMsEventType)
EVT_SET_CCDCAMERA = wx.PyEventBinder(SetCCDCameraEventType)
EVT_SET_CCDCAMERAS = wx.PyEventBinder(SetCCDCamerasEventType)
EVT_TEM_CHANGE = wx.PyEventBinder(TEMChangeEventType)
EVT_CCDCAMERA_CHANGE = wx.PyEventBinder(CCDCameraChangeEventType)

class PlayerEvent(wx.PyEvent):
	def __init__(self, state):
		wx.PyEvent.__init__(self)
		self.SetEventType(PlayerEventType)
		self.state = state

class SetImageEvent(wx.PyEvent):
	def __init__(self, image, typename=None, stats={}):
		wx.PyEvent.__init__(self)
		self.SetEventType(SetImageEventType)
		self.image = image
		self.typename = typename
		self.stats = stats

class SetTargetsEvent(wx.PyEvent):
	def __init__(self, targets, typename):
		wx.PyEvent.__init__(self)
		self.SetEventType(SetTargetsEventType)
		self.targets = targets
		self.typename = typename

class StatusUpdatedEvent(wx.PyCommandEvent):
	def __init__(self, source, level, status=None):
		wx.PyCommandEvent.__init__(self, StatusUpdatedEventType, source.GetId())
		self.SetEventObject(source)
		self.level = level
		self.status = status

class SetTEMEvent(wx.PyCommandEvent):
	def __init__(self, source, name):
		wx.PyCommandEvent.__init__(self, SetTEMEventType, source.GetId())
		self.SetEventObject(source)
		self.name = name

class SetTEMsEvent(wx.PyCommandEvent):
	def __init__(self, source, names):
		wx.PyCommandEvent.__init__(self, SetTEMsEventType, source.GetId())
		self.SetEventObject(source)
		self.names = names

class SetCCDCameraEvent(wx.PyCommandEvent):
	def __init__(self, source, name):
		wx.PyCommandEvent.__init__(self, SetCCDCameraEventType, source.GetId())
		self.SetEventObject(source)
		self.name = name

class SetCCDCamerasEvent(wx.PyCommandEvent):
	def __init__(self, source, names):
		wx.PyCommandEvent.__init__(self, SetCCDCamerasEventType, source.GetId())
		self.SetEventObject(source)
		self.names = names

class TEMChangeEvent(wx.PyCommandEvent):
	def __init__(self, source, name):
		wx.PyCommandEvent.__init__(self, TEMChangeEventType, source.GetId())
		self.SetEventObject(source)
		self.name = name

class CCDCameraChangeEvent(wx.PyCommandEvent):
	def __init__(self, source, name):
		wx.PyCommandEvent.__init__(self, CCDCameraChangeEventType, source.GetId())
		self.SetEventObject(source)
		self.name = name

