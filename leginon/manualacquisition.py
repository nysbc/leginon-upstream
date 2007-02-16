#
# COPYRIGHT:
#			 The Leginon software is Copyright 2003
#			 The Scripps Research Institute, La Jolla, CA
#			 For terms of the license agreement
#			 see	http://ami.scripps.edu/software/leginon-license
#

import data
import imagefun
import node
import project
import threading
import time
import gui.wx.ManualAcquisition
import instrument
import os
import re
import calibrationclient
import copy

class AcquireError(Exception):
	pass

class ManualAcquisition(node.Node):
	panelclass = gui.wx.ManualAcquisition.Panel
	settingsclass = data.ManualAcquisitionSettingsData
	defaultsettings = {
		'camera settings': None,
		'screen up': False,
		'screen down': False,
		'correct image': False,
		'save image': False,
		'image label': '',
		'loop pause time': 0.0,
		'low dose': False,
		'low dose pause time': 5.0,
		'defocus1switch': False,
		'defocus1': 0.0,
		'defocus2switch': False,
		'defocus2': 0.0,
	}
	def __init__(self, id, session, managerlocation, **kwargs):
		self.loopstop = threading.Event()
		self.loopstop.set()
		node.Node.__init__(self, id, session, managerlocation, **kwargs)

		self.lowdosemode = None
		self.defocus = None

		try:
			self.projectdata = project.ProjectData()
		except project.NotConnectedError:
			self.projectdata = None
		self.gridmapping = {}
		self.gridbox = None
		self.grid = None

		self.instrument = instrument.Proxy(self.objectservice,
																				self.session,
																				self.panel)

		self.dosecal = calibrationclient.DoseCalibrationClient(self)

		self.start()

	def getImageStats(self, image):
		if image is None:
			return {'mean': None, 'stdev': None, 'min': None, 'max': None}
		mean = imagefun.mean(image)
		stdev = imagefun.stdev(image, known_mean=mean)
		min = imagefun.min(image)
		max = imagefun.max(image)
		return {'mean': mean, 'stdev': stdev, 'min': min, 'max': max}

	def acquire(self):
		correct = self.settings['correct image']
		if correct:
			prefix = ''
		else:
			prefix = 'un'
		self.logger.info('Acquiring %scorrected image...' % prefix)
		self.instrument.ccdcamera.Settings = self.settings['camera settings']
		if self.settings['save image']:
			try:
				if correct:
					dataclass = data.CorrectedCameraImageData
				else:
					dataclass = data.CameraImageData
				imagedata = self.instrument.getData(dataclass)
			except Exception, e:
				self.logger.exception('Error acquiring image: %s' % e)
				raise AcquireError
			image = imagedata['image']
		else:
			if correct:
				ccdcameraname = self.instrument.getCCDCameraName()
				imagedata = self.instrument.imagecorrection.getImageData(ccdcameraname=ccdcameraname)
				image = imagedata['image']
			else:
				image = self.instrument.ccdcamera.Image

		self.logger.info('Displaying image...')
		stats = self.getImageStats(image)
		self.setImage(image, stats=stats)

		if self.settings['save image']:
			self.logger.info('Saving image to database...')
			try:
				self.publishImageData(imagedata)
			except node.PublishError, e:
				message = 'Error saving image to database'
				self.logger.info(message)
				if str(e):
					message += ' (%s)' % str(e)
				self.logger.error(message)
				raise AcquireError
		self.logger.info('Image acquisition complete')

	def preExposure(self):
		if self.settings['screen up']:
			self.instrument.tem.MainScreenPosition = 'up'

		if self.settings['low dose']:
			self.lowdosemode = self.instrument.tem.LowDoseMode
			if self.lowdosemode is None:
				self.logger.warning('Failed to save previous low dose state')
			self.instrument.tem.LowDoseMode = 'exposure'
			time.sleep(self.settings['low dose pause time'])

	def postExposure(self):
		if self.lowdosemode is not None:
			self.instrument.tem.LowDoseMode = self.lowdosemode
			self.lowdosemode = None
			time.sleep(self.settings['low dose pause time'])

		if self.settings['screen down']:
			self.instrument.tem.MainScreenPosition = 'down'

	def setImageFilename(self, imagedata):
		prefix = self.session['name']
		digits = 5
		suffix = 'ma'
		extension = 'mrc'
		if self.defocus is None:
			defindex = '_0'
		else:
			defindex = '_%d' % (self.defocus,)
		try:
			path = imagedata.mkpath()
		except Exception, e:
			raise node.PublishError(e)
		filenames = os.listdir(path)
		pattern = '^%s_[0-9]{%d}%s_[0-9].%s$' % (prefix, digits, suffix, extension)
		number = 0
		end = len('%s%s.%s' % (suffix, defindex, extension))
		for filename in filenames:
			if re.search(pattern, filename):
				n = int(filename[-digits - end:-end])
				if n > number:
					number = n
		if self.defocus != 2:
			number += 1
		if number >= 10**digits:
			raise node.PublishError('too many images, time to go home')
		filename = ('%s_%0' + str(digits) + 'd%s' + '%s') % (prefix, number, suffix, defindex)
		imagedata['filename'] = filename

	def publishImageData(self, imagedata):
		acquisitionimagedata = data.AcquisitionImageData(initializer=imagedata)
		if self.grid is not None:
			gridinfo = self.gridmapping[self.grid]
			griddata = data.GridData()
			griddata['grid ID'] = gridinfo['gridId']
			acquisitionimagedata['grid'] = griddata

		acquisitionimagedata['label'] = self.settings['image label']

		self.setImageFilename(acquisitionimagedata)

		try:
			self.publish(imagedata['scope'], database=True)
			self.publish(imagedata['camera'], database=True)
			self.publish(acquisitionimagedata, database=True)
		except RuntimeError:
			raise node.PublishError

	def acquireImage(self, dose=False):
		try:
			try:
				self.preExposure()
			except RuntimeError:
				self.panel.acquisitionDone()
				return

			try:
				if dose:
					self.measureDose()
				else:
					if self.settings['defocus1switch']:
						self.logger.info('Setting defocus 1: %s' % (self.settings['defocus1'],))
						self.instrument.tem.Defocus = self.settings['defocus1']
						self.defocus = 1
						self.acquire()
					if self.settings['defocus2switch']:
						self.logger.info('Setting defocus 2: %s' % (self.settings['defocus2'],))
						self.instrument.tem.Defocus = self.settings['defocus2']
						self.defocus = 2
						self.acquire()
					if not (self.settings['defocus1switch'] or self.settings['defocus2switch']):
						self.defocus = None
						self.acquire()
			except AcquireError:
				self.panel.acquisitionDone()
				return

			try:
				self.postExposure()
			except RuntimeError:
				self.panel.acquisitionDone()
				return
		except:
			self.panel.acquisitionDone()
			raise

		self.logger.info('Image acquired.')
		self.panel.acquisitionDone()

	def loopStarted(self):
		self.panel.loopStarted()

	def loopStopped(self):
		self.panel.loopStopped()

	def acquisitionLoop(self):
		self.logger.info('Starting acquisition loop...')

		try:
			self.preExposure()
		except RuntimeError:
			self.loopStopped()
			return

		self.loopstop.clear()
		self.logger.info('Acquisition loop started')
		self.loopStarted()
		while True:
			if self.loopstop.isSet():
				break
			try:
				self.acquire()
			except AcquireError:
				self.loopstop.set()
				break
			pausetime = self.settings['loop pause time']
			if pausetime > 0:
				self.logger.info('Pausing for ' + str(pausetime) + ' seconds...')
				time.sleep(pausetime)

		try:
			self.postExposure()
		except RuntimeError:
			self.loopStopped()
			return

		self.loopStopped()
		self.logger.info('Acquisition loop stopped')

	def acquisitionLoopStart(self):
		if not self.loopstop.isSet():
			self.loopStopped()
			return
		self.logger.info('Starting acquisition loop...')
		loopthread = threading.Thread(target=self.acquisitionLoop)
		loopthread.setDaemon(1)
		loopthread.start()

	def acquisitionLoopStop(self):
		self.logger.info('Stopping acquisition loop...')
		self.loopstop.set()

	def onSetPauseTime(self, value):
		if value < 0:
			return 0
		return value

	def cmpGridLabel(self, x, y):
		return cmp(self.gridmapping[x]['location'], self.gridmapping[y]['location'])

	def getGrids(self, label):
		gridboxes = self.projectdata.getGridBoxes()
		labelindex = gridboxes.Index(['label'])
		gridbox = labelindex[label].fetchone()
		gridboxid = gridbox['gridboxId']
		gridlocations = self.projectdata.getGridLocations()
		gridboxidindex = gridlocations.Index(['gridboxId'])
		gridlocations = gridboxidindex[gridboxid].fetchall()
		grids = self.projectdata.getGrids()
		grididindex = grids.Index(['gridId'])
		self.gridmapping = {}
		for gridlocation in gridlocations:
			grid = grididindex[gridlocation['gridId']].fetchone()
			key = '%d - %s' % (gridlocation['location'], grid['label'])
			self.gridmapping[key] = {'gridId': gridlocation['gridId'],
																'location': gridlocation['location'],
																'label': grid['label']}
		keys = self.gridmapping.keys()
		keys.sort(self.cmpGridLabel)
		return keys

	def getGridBoxes(self):
		gridboxes = self.projectdata.getGridBoxes()
		labelindex = gridboxes.Index(['label'])
		gridboxlabels = map(lambda d: d['label'], gridboxes.getall())
		gridboxlabels.reverse()
		return gridboxlabels

	def measureDose(self):
		self.logger.info('acquiring dose image')
		# configure camera using settings, but only 512x512 to save time
		origcam = self.settings['camera settings']
		# deep copy so internal dicts don't get modified
		tmpcam = copy.deepcopy(origcam)

		## cut down to 512x512, adjust offset to keep same center
		for axis in ('x','y'):
			change = origcam['dimension'][axis] - 512
			if change > 0:
				tmpcam['dimension'][axis] = 512
				tmpcam['offset'][axis] += (change / 2)

		self.instrument.ccdcamera.Settings = tmpcam

		# acquire image
		imagedata = self.instrument.getData(data.CorrectedCameraImageData)

		# display
		self.logger.info('Displaying 512x512 dose image...')
		stats = self.getImageStats(imagedata['image'])
		self.setImage(imagedata['image'], stats=stats)

		# calculate dose
		dose = self.dosecal.dose_from_imagedata(imagedata)

		dosedata = data.DoseMeasurementData()
		dosedata['dose'] = dose
		self.publish(dosedata, database=True, dbforce=True)
		self.instrument.ccdcamera.Settings = origcam
		self.logger.info('measured dose: %.3e e/A^2' % (dose/1e20,))
