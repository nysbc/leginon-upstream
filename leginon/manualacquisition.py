#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import camerafuncs
import data
import node
import project
import threading
import time
import uidata
from node import ResearchError

class AcquireError(Exception):
	pass

class ManualAcquisition(node.Node):
	def __init__(self, id, session, nodelocations, **kwargs):
		self.loopstop = threading.Event()
		self.loopstop.set()
		self.camerafuncs = camerafuncs.CameraFuncs(self)
		node.Node.__init__(self, id, session, nodelocations, **kwargs)
		self.defineUserInterface()
		self.start()

	def acquire(self):
		correct = self.correctimage.get()
		if correct:
			acquiremessage = 'Acquiring corrected image...'
		else:
			acquiremessage = 'Acquiring uncorrected image...'
		self.status.set(acquiremessage)
		try:
			imagedata = self.camerafuncs.acquireCameraImageData(correction=correct)
		except Exception, e:
			if isinstance(e, ResearchError):
				self.messagelog.error('Cannot access EM node to acquire image')
			elif isinstance(e, camerafuncs.NoCorrectorError):
				self.messagelog.error('Cannot access Corrector node to correct image')
			else:
				self.messagelog.error('Error acquiring image')
			self.status.set('Error acquiring image')
			raise AcquireError
		self.status.set('Displaying image...')
		self.image.set(imagedata['image'])
		if self.usedatabase.get():
			self.status.set('Saving image to database')
			self.publishImageData(imagedata)
		self.status.set('Image acquisition complete')

	def publishImageData(self, imagedata):
		acquisitionimagedata = data.AcquisitionImageData(initializer=imagedata)
		acquisitionimagedata['id'] = self.ID()
		grid = self.gridselect.getSelectedValue()
		acquisitionimagedata['gridId'] = self.gridmapping[grid]['gridId']
		self.publish(acquisitionimagedata, database=True)

	def acquireImage(self):
		self.acquiremethod.disable()
		self.startmethod.disable()
		try:
			self.acquire()
		except AcquireError:
			pass
		self.acquiremethod.enable()
		self.startmethod.enable()

	def acquisitionLoop(self):
		self.loopstop.clear()
		self.status.set('Acquisition loop started')
		while True:
			if self.loopstop.isSet():
				break
			try:
				self.acquire()
			except AcquireError:
				self.loopstop.set()
				break
			pausetime = self.pausetime.get()
			if pausetime > 0:
				self.status.set('Pausing for ' + str(pausetime) + ' seconds...')
				time.sleep(pausetime)
		self.acquiremethod.enable()
		self.startmethod.enable()
		self.stopmethod.disable()
		self.status.set('Acquisition loop stopped')

	def acquisitionLoopStart(self):
		if not self.loopstop.isSet():
			return
		self.status.set('Starting acquisition loop...')
		self.acquiremethod.disable()
		self.startmethod.disable()
		self.stopmethod.enable()
		loopthread = threading.Thread(target=self.acquisitionLoop)
		loopthread.setDaemon(1)
		loopthread.start()

	def acquisitionLoopStop(self):
		self.status.set('Stopping acquisition loop...')
		self.loopstop.set()

	def onSetPauseTime(self, value):
		if value < 0:
			return 0
		return value

	def onGridBoxSelect(self, value):
		projectdata = project.ProjectData()
		if not projectdata.isConnected():
			self.gridboxselect.set(['None'], 0)
			self.gridselect.setList(['None'])
			return 0

		label = self.gridboxselect.getSelectedValue(value)

		if label == 'None':
			self.gridselect.set(['None'], 0)
		else:
			gridboxes = projectdata.getGridBoxes()
			labelindex = gridboxes.Index(['label'])
			gridbox = labelindex[label].fetchone()
			gridboxid = gridbox['gridboxId']
			gridlocations = projectdata.getGridLocations()
			gridboxidindex = gridlocations.Index(['gridboxId'])
			gridlocations = gridboxidindex[gridboxid].fetchall()
			grids = projectdata.getGrids()
			grididindex = grids.Index(['gridId'])
			self.gridmapping = {}
			for gridlocation in gridlocations:
				grid = grididindex[gridlocation['gridId']].fetchone()
				self.gridmapping[grid['label']] = {'gridId': gridlocation['gridId'],
																					'location': gridlocation['location']}
			self.gridselect.set(['None'] + self.gridmapping.keys(), 0)
			self.gridmapping['None'] = None

		return value

	def updateGridBoxSelection(self):
		projectdata = project.ProjectData()
		if not projectdata.isConnected():
			self.gridboxselect.set(['None'], 0)
			return

		gridboxes = projectdata.getGridBoxes()
		labelindex = gridboxes.Index(['label'])
		gridboxlabels = map(lambda d: d['label'], gridboxes.getall())
		gridboxlabels.append('None')
		gridboxlabels.reverse()
		self.gridboxselect.set(gridboxlabels, 0)

	def defineUserInterface(self):
		node.Node.defineUserInterface(self)

		self.messagelog = uidata.MessageLog('Message Log')
		self.status = uidata.String('Status', '', 'r')
		statuscontainer = uidata.Container('Status')
		statuscontainer.addObjects((self.status,))

		self.image = uidata.Image('Image', None, 'rw')

		self.gridboxselect = uidata.SingleSelectFromList('Grid Box', None, None,
																											'rw')
		self.gridselect = uidata.SingleSelectFromList('Grid', None, None, 'rw')
		self.gridboxselect.setCallback(self.onGridBoxSelect)
		self.updateGridBoxSelection()
		refreshmethod = uidata.Method('Refresh', self.updateGridBoxSelection)

		gridcontainer = uidata.Container('Current Grid')
		gridcontainer.addObjects((self.gridboxselect, self.gridselect,
															refreshmethod))

		self.correctimage = uidata.Boolean('Correct image', True, 'rw',
																				persist=True)
		camerafuncscontainer = self.camerafuncs.uiSetupContainer()
		self.pausetime = uidata.Number('Loop pause time (seconds)', 0.0, 'rw',
																		callback=self.onSetPauseTime, persist=True)
		self.usedatabase = uidata.Boolean('Save image to database', True, 'rw',
																			persist=True)
		settingscontainer = uidata.Container('Settings')
		settingscontainer.addObjects((gridcontainer, self.correctimage,
																	camerafuncscontainer,
																	self.pausetime, self.usedatabase))

		self.acquiremethod = uidata.Method('Acquire', self.acquireImage)
		self.startmethod = uidata.Method('Start', self.acquisitionLoopStart)
		self.stopmethod = uidata.Method('Stop', self.acquisitionLoopStop)
		self.stopmethod.disable()
		loopcontainer = uidata.Container('Acquisition Loop')
		loopcontainer.addObjects((self.startmethod, self.stopmethod))
		controlcontainer = uidata.Container('Control')
		controlcontainer.addObjects((self.acquiremethod, loopcontainer))

		container = uidata.LargeContainer('Manual Acquisition')
		container.addObjects((self.messagelog, statuscontainer, self.image,
													settingscontainer, controlcontainer))
		self.uiserver.addObject(container)

