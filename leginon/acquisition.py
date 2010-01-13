#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#
'''
Acquisition node is a TargetWatcher, so it receives either an ImageTargetData
or an ImageTargetListData.  The method processTargetData is called on each
ImageTargetData.
'''
import targetwatcher
import time
import leginondata
import event
import calibrationclient
import presets
import copy
import threading
import node
import instrument
import gui.wx.Acquisition
import gui.wx.Presets
import navigator
import numpy
import math
from pyami import arraystats, imagefun, ordereddict
import smtplib
import emailnotification
import leginonconfig
import gridlabeler

debug = False

class NoMoveCalibration(targetwatcher.PauseRepeatException):
	pass

class InvalidPresetsSequence(targetwatcher.PauseRepeatException):
	pass

class BadImageStatsPause(targetwatcher.PauseRepeatException):
	pass

class BadImageStatsAbort(Exception):
	pass

class InvalidStagePosition(Exception):
	pass

def setImageFilename(imagedata):
	if imagedata['filename'] is not None:
		return
	listlabel = ''
	numberstr = '%05d' % (imagedata['target']['number'],)
	if imagedata['target']['list'] is not None:
		listlabel = imagedata['target']['list']['label']
	if imagedata['preset'] is None:
		presetstr = ''
	else:
		presetstr = imagedata['preset']['name']
	mystr = numberstr + presetstr
	rootname = getRootName(imagedata, listlabel)
	parts = []
	parts.append(rootname)
	if listlabel:
		parts.append(listlabel)
	parts.append(mystr)
	if imagedata['version']:
		vstr = 'v%02d' % (imagedata['version'],)
		parts.append(vstr)

	filename = '_'.join(parts)
	imagedata['filename'] = filename

def getRootName(imagedata, listlabel=False):
	'''
	get the root name of an image from its parent
	'''
	parent_target = imagedata['target']
	usegridlabel = not listlabel
	if parent_target is None:
		## there is no parent target
		## create my own root name
		return newRootName(imagedata, usegridlabel)

	parent_image = parent_target['image']
	if parent_image is None:
		## there is no parent image
		return newRootName(imagedata, usegridlabel)

	## use root name from parent image
	parent_root = parent_image['filename']
	if parent_root:
		return parent_root
	else:
		return newRootName(imagedata, usegridlabel)

def newRootName(imagedata, usegridlabel):
	parts = []
	sessionstr = imagedata['session']['name']
	parts.append(sessionstr)
	if usegridlabel:
		if 'grid' in imagedata and imagedata['grid'] is not None:
			gridlabel = gridlabeler.getGridLabel(imagedata['grid'])
			parts.append(gridlabel)
	sep = '_'
	name = sep.join(parts)
	return name


class Acquisition(targetwatcher.TargetWatcher):
	panelclass = gui.wx.Acquisition.Panel
	settingsclass = leginondata.AcquisitionSettingsData
	# maybe not a class attribute
	defaultsettings = {
		'pause time': 2.5,
		'move type': 'image shift',
		'preset order': [],
		'correct image': True,
		'display image': True,
		'save image': True,
		'wait for process': False,
		'wait for rejects': False,
		'wait for reference': False,
		#'duplicate targets': False,
		#'duplicate target type': 'focus',
		'iterations': 1,
		'wait time': 0,
		'adjust for transform': 'no',
		'drift between': False,
		'mover': 'presets manager',
		'move precision': 0.0,
		'accept precision': 1e-3,
		'process target type': 'acquisition',
		'save integer': False,
		'background': False,
		'use parent tilt': False,
		'adjust time by tilt': False,
		'reset tilt': False,
		'high mean': 2**16,
		'low mean': 50,
		'bad stats response': 'Continue',
		'emission off': False,
		'target offset row': 0,
		'target offset col': 0,
		'correct image shift coma': False,
	}
	eventinputs = targetwatcher.TargetWatcher.eventinputs \
								+ [event.DriftMonitorResultEvent,
										event.MakeTargetListEvent,
										event.ImageProcessDoneEvent,
										event.AcquisitionImagePublishEvent] \
								+ presets.PresetsClient.eventinputs \
								+ navigator.NavigatorClient.eventinputs
	eventoutputs = targetwatcher.TargetWatcher.eventoutputs \
									+ [event.LockEvent,
											event.UnlockEvent,
											event.AcquisitionImagePublishEvent,
	event.ChangePresetEvent, event.PresetLockEvent, event.PresetUnlockEvent,
											event.DriftMonitorRequestEvent, 
											event.FixBeamEvent,
											event.ImageListPublishEvent, event.ReferenceTargetPublishEvent] \
											+ navigator.NavigatorClient.eventoutputs

	def __init__(self, id, session, managerlocation, **kwargs):

		targetwatcher.TargetWatcher.__init__(self, id, session, managerlocation, **kwargs)

		self.addEventInput(event.AcquisitionImagePublishEvent, self.handleDriftImage)
		self.addEventInput(event.DriftMonitorResultEvent, self.handleDriftResult)
		self.addEventInput(event.ImageProcessDoneEvent, self.handleImageProcessDone)
		self.addEventInput(event.MakeTargetListEvent, self.setGrid)
		self.driftdone = threading.Event()
		self.driftimagedone = threading.Event()
		self.instrument = instrument.Proxy(self.objectservice, self.session)

		self.calclients = ordereddict.OrderedDict()
		self.calclients['image shift'] = calibrationclient.ImageShiftCalibrationClient(self)
		self.calclients['stage position'] = calibrationclient.StageCalibrationClient(self)
		self.calclients['modeled stage position'] = calibrationclient.ModeledStageCalibrationClient(self)
		self.calclients['image beam shift'] = calibrationclient.ImageBeamShiftCalibrationClient(self)
		self.calclients['beam shift'] = calibrationclient.BeamShiftCalibrationClient(self)
		self.calclients['beam tilt'] = calibrationclient.BeamTiltCalibrationClient(self)

		self.presetsclient = presets.PresetsClient(self)
		self.navclient = navigator.NavigatorClient(self)
		self.doneevents = {}
		self.onTarget = False
		self.imagelistdata = None
		self.simloopstop = threading.Event()
		self.received_image_drift = threading.Event()
		self.requested_drift = None
		self.grid = None

		self.duplicatetypes = ['acquisition', 'focus']
		self.presetlocktypes = ['acquisition', 'target', 'target list']

		if debug:
			self.timedebug = {}

		self.start()

	def checkSettings(self, settings):
		problems = []
		return problems
		presetnames = settings['preset order']
		for presetname in presetnames:
			try:
				self.presetsclient.getPresetFromDB(presetname)
			except:
				problems.append(('error','Preset "%s" does not exist.  Create it, or import from a previous session' % (presetname,)))
				continue
			for type in ('dark', 'norm'):
				for channel in (0,1):
					exists = self.presetsclient.correctorImageExists(presetname, type, channel)
					if not exists:
						problems.append(('error','Preset "%s" Missing %s CCD image, channel %s' % (presetname, type, channel)))

		return problems

	def onPresetPublished(self, evt):
		evt = gui.wx.Presets.NewPresetEvent()
		self.panel.GetEventHandler().AddPendingEvent(evt)

	def handleDriftResult(self, ev):
		driftresult = ev['data']
		status = driftresult['status']
		final = driftresult['final']
		drift = numpy.hypot(final['rowmeters'],final['colmeters']) / final['interval']
		self.reportStatus('acquisition', 'Received drift result status "%s", final drift: %.3e' % (status, drift))
		self.driftresult = driftresult
		self.driftdone.set()

	def handleDriftImage(self, ev):
		driftimage = ev['data']
		self.reportStatus('acquisition', 'Received drift image')
		self.driftimage = driftimage
		self.driftimagedone.set()

	def handleImageProcessDone(self, ev):
		imageid = ev['imageid']
		status = ev['status']
		if imageid in self.doneevents:
			self.doneevents[imageid]['status'] = status
			self.doneevents[imageid]['received'].set()

	def processData(self, newdata):
		if isinstance(newdata, leginondata.QueueData):
			self.processTargetListQueue(newdata)
			return
		self.logger.info('Acquisition.processData')
		self.imagelistdata = leginondata.ImageListData(session=self.session,
																						targets=newdata)
		self.publish(self.imagelistdata, database=True)
		targetwatcher.TargetWatcher.processData(self, newdata)
		self.publish(self.imagelistdata, pubevent=True)
		self.presetsclient.unlock()
		self.logger.info('Acquisition.processData done')

	def validateStagePosition(self, stageposition):
		## check for out of stage range target
		stagelimits = {
			'x': (-9.9e-4, 9.9e-4),
			'y': (-9.9e-4, 9.9e-4),
		}
		for axis, limits in stagelimits.items():
			if stageposition[axis] < limits[0] or stageposition[axis] > limits[1]:
				pstr = '%s: %g' % (axis, stageposition[axis])
				messagestr = 'Aborting target: stage position %s out of range' % pstr
				self.logger.info(messagestr)
				raise InvalidStagePosition(messagestr)

	def validatePresets(self):
		presetorder = self.settings['preset order']
		if not presetorder:
			raise InvalidPresetsSequence('no presets configured')
		availablepresets = self.getPresetNames()
		for presetname in presetorder:
			if presetname not in availablepresets:
				raise InvalidPresetsSequence('bad preset %s in presets order' % (presetname,))

	def makeTransformTarget(self, target, offset):
		newtarget = leginondata.AcquisitionImageTargetData(initializer=target)
		# Fix here about version
		newtarget['delta row'] = target['delta row'] + offset['y']
		newtarget['delta column'] = target['delta column'] + offset['x']
		newtarget['fromtarget'] = target
		newtarget.insert(force=True)
		self.logger.info('target adjusted by (%.1f,%.1f) (column, row)' % (offset['x'],offset['y']))
		return newtarget
	
	def transformTarget(self, target, level):
		parentimage = target['image']
		matrix = self.lookupMatrix(parentimage)
		if parentimage is None:
			return target
		## check all transforms declared to decide on minimum mag
		## for now there is only one
		minimum_mag = self.settings['min mag']
		if parentimage['preset']['magnification'] < minimum_mag:
			self.logger.info('not transforming target because parent image has low mag')
			return target
		if matrix is None:
			parenttarget = parentimage['target']
			if level == 'all':
				newparenttarget = self.transformTarget(parenttarget, level)
			elif level == 'one':
				newparenttarget = parenttarget
			newparentimage = self.reacquire(newparenttarget)
			if newparentimage is None:
				return None
			matrix = self.calculateMatrix(parentimage, newparentimage)
		newtarget = self.matrixTransform(target, matrix,newparentimage)
		return newtarget
	def adjustTargetForTransform(self, targetdata):
		## look up most recent version of this target
		targetlist = targetdata['list']
		targetnumber = targetdata['number']
		newtargetdata = self.researchTargets(session=self.session, number=targetnumber, list=targetlist, status='new')
		# this is the most recent version with status "new"
		newtargetdata = newtargetdata[0]
		
		## look up all transforms declared for this session
		decq = leginondata.TransformDeclaredData(session=self.session)
		transformsdeclared = decq.query()

		## if no transforms declared, return recent target
		if not transformsdeclared:
			return newtargetdata

		## if recent target after transforms declared, return recent target
		newtargettime = newtargetdata.timestamp
		declaredtime = transformsdeclared[0].timestamp
		if newtargettime > declaredtime:
			return newtargetdata

		## if transform declared after most recent target, need new transformed	target
		newtargetdata = self.requestTransformTarget(newtargetdata)
			
		## make sure we move to new target
		self.onTarget = False
		return newtargetdata

	def processTargetData(self, targetdata, attempt=None):
		'''
		This is called by TargetWatcher.processData when targets available
		If called with targetdata=None, this simulates what occurs at
		a target (going to presets, acquiring images, etc.)
		'''

		try:
			self.validatePresets()
		except InvalidPresetsSequence, e:
			if targetdata is None or targetdata['type'] == 'simulated':
				## don't want to repeat in this case
				self.logger.error(str(e))
				return 'aborted'
			else:
				raise

		presetnames = self.settings['preset order']
		ret = 'ok'
		self.onTarget = False
		for newpresetname in presetnames:
			if self.alreadyAcquired(targetdata, newpresetname):
				continue

			if targetdata is not None and targetdata['type'] != 'simulated' and self.settings['adjust for transform'] != 'no':
				if self.settings['drift between'] and self.goodnumber > 0:
					self.declareDrift('between targets')
				targetonimage = targetdata['delta column'],targetdata['delta row']
				targetdata = self.adjustTargetForTransform(targetdata)
				self.logger.info('target adjusted by (%.1f,%.1f) (column, row)' % (targetdata['delta column']-targetonimage[0],targetdata['delta row']-targetonimage[1]))
			offset = {'x':self.settings['target offset col'],'y':self.settings['target offset row']}
			if offset['x'] or offset['y']:
				targetdata = self.makeTransformTarget(targetdata,offset)
			### determine how to move to target
			try:
				emtarget = self.targetToEMTargetData(targetdata)
			except InvalidStagePosition:
				return 'invalid'

			presetdata = self.presetsclient.getPresetByName(newpresetname)

			### acquire film or CCD
			self.startTimer('acquire')
			ret = self.acquire(presetdata, emtarget, attempt=attempt, target=targetdata)
			self.stopTimer('acquire')
			# in these cases, return immediately
			if ret in ('aborted', 'repeat'):
				self.reportStatus('acquisition', 'Acquisition state is "%s"' % ret)
				break
			if ret == 'repeat':
				return repeat

		self.reportStatus('processing', 'Processing complete')

		return ret

	def alreadyAcquired(self, targetdata, presetname):
		'''
		determines if image already acquired using targetdata and presetname
		'''
		## if image exists with targetdata and presetdata, no acquire
		## we expect target to be exact, however, presetdata may have
		## changed so we only query on preset name

		# seems to have trouple with using original targetdata as
		# a query, so use a copy with only some of the fields
		presetquery = leginondata.PresetData(name=presetname)
		## don't care if drift correction was done on target after image was
		## acquired, so ignore version, delta row/col
		targetquery = leginondata.AcquisitionImageTargetData(initializer=targetdata)
		targetquery['version'] = None
		targetquery['delta row'] = None
		targetquery['delta column'] = None
		imagequery = leginondata.AcquisitionImageData(target=targetquery, preset=presetquery)
		## other things to fill in
		imagequery['scope'] = leginondata.ScopeEMData()
		imagequery['camera'] = leginondata.CameraEMData()
		imagequery['session'] = leginondata.SessionData()

		datalist = self.research(datainstance=imagequery)
		if datalist:
			## no need to acquire again, but need to republish
			self.reportStatus('output', 'Image was acquired previously, republishing')
			imagedata = datalist[0]
			self.publishDisplayWait(imagedata)
			return True
		else:
			return False

	def targetToEMTargetData(self, targetdata):
		'''
		convert an ImageTargetData to an EMTargetData object
		using chosen move type.
		The result is a valid scope state that will center
		the target on the camera, but not necessarily at the
		desired preset.  It is shifted from the preset of the 
		original targetdata.

		Certain fields are reset to None becuase they are not
		necessary, and cause problems if used between different
		magnification modes (LM, M, SA).
		'''
		emtargetdata = leginondata.EMTargetData()
		if targetdata is not None:
			# get relevant info from target data
			targetdeltarow = targetdata['delta row']
			targetdeltacolumn = targetdata['delta column']
			origscope = targetdata['scope']
			targetscope = leginondata.ScopeEMData(initializer=origscope)
			## copy these because they are dictionaries that could
			## otherwise be shared (although transform() should be
			## smart enough to create copies as well)
			targetscope['stage position'] = dict(origscope['stage position'])
			targetscope['image shift'] = dict(origscope['image shift'])
			targetscope['beam shift'] = dict(origscope['beam shift'])

			movetype = self.settings['move type']
			oldpreset = targetdata['preset']

			zdiff = 0.0
			### simulated target does not require transform
			if targetdata['type'] == 'simulated':
				newscope = origscope
			else:
				targetcamera = targetdata['camera']
		
				## to shift targeted point to center...
				deltarow = -targetdeltarow
				deltacol = -targetdeltacolumn
		
				pixelshift = {'row':deltarow, 'col':deltacol}
		
				## figure out scope state that gets to the target
				calclient = self.calclients[movetype]
				try:
					newscope = calclient.transform(pixelshift, targetscope, targetcamera)
				except calibrationclient.NoMatrixCalibrationError, e:
					raise NoMoveCalibration(e)

				## if stage is tilted and moving by image shift,
				## calculate z offset between center of image and target
				if movetype in ('image shift','image beam shift','beam shift') and abs(targetscope['stage position']['a']) > 0.02:
					calclient = self.calclients['stage position']
					try:
						tmpscope = calclient.transform(pixelshift, targetscope, targetcamera)
					except calibrationclient.NoMatrixCalibrationError,e:
						raise NoMoveCalibration(e)
					ydiff = tmpscope['stage position']['y'] - targetscope['stage position']['y']
					zdiff = ydiff * numpy.sin(targetscope['stage position']['a'])
	
			### check if stage position is valid
			if newscope['stage position']:
				self.validateStagePosition(newscope['stage position'])

			emtargetdata['preset'] = oldpreset
			emtargetdata['movetype'] = movetype
			emtargetdata['image shift'] = dict(newscope['image shift'])
			emtargetdata['beam shift'] = dict(newscope['beam shift'])
			emtargetdata['stage position'] = dict(newscope['stage position'])
			emtargetdata['delta z'] = zdiff

		emtargetdata['target'] = targetdata

		## publish in DB because it will likely be needed later
		## when returning to the same target,
		## even after it is removed from memory
		self.publish(emtargetdata, database=True)
		return emtargetdata

	def lastFilmAcquisition(self):
		filmdata = self.research(datainstance=leginondata.FilmData(), results=1)
		if filmdata:
			filmdata = filmdata[0]
		else:
			filmdata = None
		return filmdata

	def setImageFilename(self, imagedata):
		setImageFilename(imagedata)

	def acquireFilm(self, presetdata, emtarget=None):
		## get current film parameters
		stock = self.instrument.tem.FilmStock
		if stock < 1:
			self.logger.error('Film stock = %s. Film exposure failed' % (stock,))
			return 'no stock'
		## create FilmData(AcquisitionImageData) which 
		## will be used to store info about this exposure
		targetdata = emtarget['target']
		filmdata = leginondata.FilmData(session=self.session, preset=presetdata, label=self.name, target=targetdata, emtarget=emtarget)

		## first three of user name
		self.instrument.tem.FilmUserCode = self.session['user']['name'][:3]
		## use next dbid for film text
		last_film = self.lastFilmAcquisition()
		if last_film is None:
			last_dbid = 0
		else:
			last_dbid = last_film.dbid
		next_dbid = last_dbid + 1
		self.instrument.tem.FilmText = 'DB key = %d' % (next_dbid,)
		self.instrument.tem.FilmDateType = 'YY.MM.DD'

		## get scope for database
		scopebefore = self.instrument.getData(leginondata.ScopeEMData)
		filmdata['scope'] = scopebefore
		## insert film
		self.instrument.tem.preFilmExposure(True)
		# expose film
		self.instrument.ccdcamera.getImage()
		## take out film
		self.instrument.tem.postFilmExposure(True)
		return filedata

	def exposeSpecimen(self, seconds):
		## I want to expose the specimen, but not the camera.
		## I would rather use some kind of manual shutter where above specimen
		## shutter opens and below specimen shutter remains closed.
		## Using the screen down was easier and serves the same purpose, but
		## with more error on the actual time exposed.
		self.logger.info('Screen down for %ss to expose specimen...' % (seconds,))
		self.instrument.tem.MainScreenPosition = 'down'
		time.sleep(seconds)
		self.instrument.tem.MainScreenPosition = 'up'
		self.logger.info('Screen up.')

	def getImageShiftOffset(self):
		pimageshift = self.presetsclient.currentpreset['image shift']
		simageshift = self.instrument.tem.ImageShift
		offsetx = simageshift['x'] - pimageshift['x']
		offsety = simageshift['y'] - pimageshift['y']
		return {'x': offsetx, 'y': offsety}

	def setImageShiftOffset(self, imageshift):
		simageshift = self.instrument.tem.ImageShift
		x = simageshift['x'] + imageshift['x']
		y = simageshift['y'] + imageshift['y']
		self.instrument.tem.ImageShift = {'x':x, 'y':y}

	def moveAndPreset(self, presetdata, emtarget):
			status = 'ok'
			presetname = presetdata['name']
			targetdata = emtarget['target']
			#### move and change preset
			movetype = self.settings['move type']
			movefunction = self.settings['mover']
			keep_shift = False
			if movetype == 'image shift' and movefunction == 'navigator':
				self.logger.warning('Navigator cannot be used for image shift, using Presets Manager instead')
				movefunction = 'presets manager'
			self.setStatus('waiting')
			if movefunction == 'navigator':
				emtarget = None
				if not self.onTarget and targetdata['type'] != 'simulated':
					precision = self.settings['move precision']
					accept_precision = self.settings['accept precision']
					final_imageshift = self.settings['final image shift']
					if final_imageshift:
						keep_shift = True
					status = self.navclient.moveToTarget(targetdata, movetype, precision, accept_precision, final_imageshift=final_imageshift)
					if status == 'error':
						return status
			self.presetsclient.toScope(presetname, emtarget, keep_shift=keep_shift)
			stageposition = self.instrument.tem.getStagePosition()
			stagea = stageposition['a']
			if self.settings['correct image shift coma']:
				## beam tilt correction induced by image shift
				beamtiltclient = self.calclients['beam tilt']
				tem = self.instrument.getTEMData()
				cam = self.instrument.getCCDCameraData()
				ht = self.instrument.tem.HighTension
				mag = self.instrument.tem.Magnification
				imageshift = self.instrument.tem.getImageShift()
				self.beamtilt0 = self.instrument.tem.getBeamTilt()
				try:
					beamtilt = beamtiltclient.transformImageShiftToBeamTilt(imageshift, tem, cam, ht, self.beamtilt0, mag)
					self.instrument.tem.BeamTilt = beamtilt
				except Exception, e:
					raise NoMoveCalibration(e)
			if self.settings['adjust time by tilt'] and abs(stagea) > 10 * 3.14159 / 180:
				camdata = leginondata.CameraEMData()
				camdata.friendly_update(presetdata)
				old_time = camdata['exposure time']
				new_time = old_time / math.cos(stagea)
				if new_time > 5000 or new_time <= 1:
					self.logger.warning('Ignore unreasonable exposure time at %d ms' % new_time)
					new_time = old_time
				camdata['exposure time'] = new_time
				self.logger.info('scale exposure time from %d to %d by cos(%d)' % (old_time,new_time,int(stagea*180/3.14159)))
				self.instrument.setData(camdata)
			self.onTarget = True
			self.setStatus('processing')
			return status

	def acquireCCD(self, presetdata, emtarget=None,channel=None):
		targetdata = emtarget['target']
		## set correction channel
		## in the future, may want this based on preset or something
		if channel is None:
			channel = 0
		else:
			channel = channel
		## acquire image
		self.reportStatus('acquisition', 'acquiring image...')
		self.startTimer('acquire getData')
		correctimage = self.settings['correct image']
		if correctimage:
			imagedata = self.acquireCorrectedCameraImageData(channel=channel)
		else:
			imagedata = self.acquireCameraImageData()
		self.reportStatus('acquisition', 'image acquired')
		self.stopTimer('acquire getData')
		if imagedata is None:
			return 'fail'

		if self.settings['bad stats response'] != 'Continue':
			self.evaluateStats(imagedata['image'])

		## convert float to uint16
		if self.settings['save integer']:
			imagedata['image'] = numpy.clip(imagedata['image'], 0, 2**16-1)
			imagedata['image'] = numpy.asarray(imagedata['image'], numpy.uint16)

		## convert CameraImageData to AcquisitionImageData
		dim = imagedata['camera']['dimension']
		pixels = dim['x'] * dim['y']
		pixeltype = str(imagedata['image'].dtype)
		imagedata = leginondata.AcquisitionImageData(initializer=imagedata, preset=presetdata, label=self.name, target=targetdata, list=self.imagelistdata, emtarget=emtarget, pixels=pixels, pixeltype=pixeltype)
		imagedata['version'] = 0
		## store EMData to DB to prevent referencing errors
		self.publish(imagedata['scope'], database=True)
		self.publish(imagedata['camera'], database=True)
		return imagedata

	def acquire(self, presetdata, emtarget=None, attempt=None, target=None, channel=None):


		if debug:
			try:
				tnum = emtarget['target']['number']
				tkey = emtarget.dbid
			except:
				tnum = None
				tkey = None
			print tnum, 'MOVEANDPRESETPAUSE START'
			t0 = time.time()
			self.timedebug[tkey] = t0
			if 'consecutive' in self.timedebug:
				print tnum, '************************************* CONSECUTIVE', t0 - self.timedebug['consecutive']
			self.timedebug['consecutive'] = t0

		status = self.moveAndPreset(presetdata, emtarget)
		if status == 'error':
			self.logger.warning('Move failed. skipping acquisition at this target')
			return status

		pausetime = self.settings['pause time']

		if debug:
			print tnum, 'PAUSING FOR', pausetime

		self.startTimer('pause')
		time.sleep(pausetime)
		self.stopTimer('pause')

		if debug:
			print tnum, 'MOVEANDPRESETPAUSE DONE', time.time() - t0

		## pre-exposure
		pretime = presetdata['pre exposure']
		if pretime:
			self.exposeSpecimen(pretime)
		args = (presetdata, emtarget, channel)
		if self.settings['background']:
			self.clearCameraEvents()
			t = threading.Thread(target=self.acquirePublishDisplayWait, args=args)
			t.start()
			self.waitExposureDone()
		else:
			self.acquirePublishDisplayWait(*args)
		return status

	def acquirePublishDisplayWait(self, presetdata, emtarget, channel):
		if debug:
			try:
				tnum = emtarget['target']['number']
				tkey = emtarget.dbid
			except:
				tnum = None
				tkey = None
			print tnum, 'APDW START'
			t0 = time.time()

		if presetdata['film']:
			imagedata = self.acquireFilm(presetdata, emtarget)
		else:
			imagedata = self.acquireCCD(presetdata, emtarget, channel=channel)

		self.imagedata = imagedata
		if self.settings['correct image shift coma']:
			print "beam tilt for image acquired",self.instrument.tem.BeamTilt
			self.instrument.tem.BeamTilt = self.beamtilt0
			print "resetted beam tilt",self.instrument.tem.BeamTilt
		targetdata = emtarget['target']
		if targetdata is not None and 'grid' in targetdata and targetdata['grid'] is not None:
			imagedata['grid'] = targetdata['grid']
		else:
			if self.grid:
				imagedata['grid'] = self.grid
		self.publishDisplayWait(imagedata)

		if debug:
			print tnum, 'APDW DONE', time.time() - t0
			ttt = time.time() - self.timedebug[tkey]
			del self.timedebug[tkey]
			print tnum, '************* TOTAL ***', ttt

	def publishDisplayWait(self, imagedata):
		'''
		publish image data, display it, then wait for something to 
		process it
		'''
		## set the 'filename' value
		self.setImageFilename(imagedata)

		## set pixel size so mrc file will have it in header
		imagedata.attachPixelSize()

		self.reportStatus('output', 'Publishing image...')
		self.startTimer('publish image')
		if self.settings['save image']:
			imagedata.insert(force=True)
		self.publish(imagedata, pubevent=True)

		## set up to handle done events
		dataid = imagedata.dbid
		doneevent = {}
		doneevent['received'] = threading.Event()
		doneevent['status'] = 'waiting'
		self.doneevents[dataid] = doneevent

		self.stopTimer('publish image')
		self.reportStatus('output', 'Image published')
		self.reportStatus('output', 'Publishing stats...')
		self.startTimer('publish stats')
		self.publishStats(imagedata)
		self.stopTimer('publish stats')
		self.reportStatus('output', 'Stats published...')

		if self.settings['display image']:
			self.reportStatus('output', 'Displaying image...')
			self.startTimer('display')
			self.setImage(numpy.asarray(imagedata['image'], numpy.float32), 'Image')
			self.stopTimer('display')
			self.reportStatus('output', 'Image displayed')

		if self.settings['wait for process']:
			self.setStatus('waiting')
			self.startTimer('waitForImageProcess')
			self.waitForImageProcessDone()
			self.stopTimer('waitForImageProcess')
			if not self.settings['background']:
				self.setStatus('processing')
			else:
				self.setStatus('idle')
		return 'ok'

	def publishStats(self, imagedata):
		im = imagedata['image']
		if im is None:
			return
		allstats = arraystats.all(im)
		statsdata = leginondata.AcquisitionImageStatsData()
		statsdata['session'] = self.session
		statsdata['min'] = allstats['min']
		statsdata['max'] = allstats['max']
		statsdata['mean'] = allstats['mean']
		statsdata['stdev'] = allstats['std']
		statsdata['image'] = imagedata
		self.publish(statsdata, database=True)

	def setEmailPassword(self, password):
		self.emailpassword = password

	def emailBadImageStats(self, stats):
		s = smtplib.SMTP()
		s.connect(leginonconfig.emailhost)
		s.login(leginonconfig.emailuser, self.emailpassword)

		subject = 'LEGINON: bad image stats'
		responsetext = self.settings['bad stats response'].replace('Abort','aborted')
		responsetext = responsetext.replace('Pause','paused at current')
		text = 'Your Leginon session has '+ responsetext + ' target list(s) at \n\n'+time.ctime() + '\n\n due to bad image mean value of %.2f' %stats
		mes = emailnotification.makeMessage(leginonconfig.emailfrom, leginonconfig.emailto, subject, text)
		s.sendmail(leginonconfig.emailfrom, leginonconfig.emailto, mes.as_string())

	def respondBadImageStats(self, badstate=''):
			if self.settings['bad stats response'] == 'Abort all':
				self.player.stopqueue()
				self.logger.info('Stopping all targets in queue')
				raise BadImageStatsAbort('image mean too '+badstate)
			elif self.settings['bad stats response'] == 'Abort one':
				self.player.stop()
				self.logger.info('Skiping targets in this target list')
				raise BadImageStatsAbort('image mean too '+badstate)
			elif self.settings['bad stats response'] == 'Pause':
				raise BadImageStatsPause('image mean too '+badstate)

	def evaluateStats(self, imagearray):
		mean = arraystats.mean(imagearray)
		if mean > self.settings['high mean']:
			try:
				self.emailBadImageStats(mean)
			except:
				self.logger.info('could not email')
			self.respondBadImageStats('high')
		if mean < self.settings['low mean']:
			try:
				self.emailBadImageStats(mean)
			except:
				self.logger.info('could not email')
			self.respondBadImageStats('low')

	def publishImage(self, imdata):
		self.publish(imdata, pubevent=True)

	def waitForImageProcessDone(self):
		imageids = self.doneevents.keys()
		imageidstrs = map(str, imageids)
		# wait for image processing nodes to complete
		for id, eventinfo in self.doneevents.items():
			self.reportStatus('processing', 'Waiting for %s to be processed' % (id,))
			eventinfo['received'].wait()
			idstr = str(id)
			imageidstrs.remove(idstr)
			self.reportStatus('processing', 'Done waiting for %s to be processed' % (id,))
		self.doneevents.clear()
		self.reportStatus('processing', 'Done waiting for images to be processed')

	def stopWaitingForImage(self):
		imageidstr = self.waitingforimages.getSelectedValue()
		try:
			imageid = eval(imageidstr)
		except TypeError:
			return
		if imageid in self.doneevents:
			self.doneevents[imageid]['received'].set()
			self.doneevents[imageid]['status'] = 'forced'

	def getPresetNames(self):
		presetnames = self.presetsclient.getPresetNames()
		return presetnames

	def checkDrift(self, presetname, emtarget, threshold):
		'''
		request DriftManager to monitor drift
		'''
		driftdata = leginondata.DriftMonitorRequestData(session=self.session, presetname=presetname, emtarget=emtarget, threshold=threshold)
		self.driftdone.clear()
		self.driftimagedone.clear()
		self.publish(driftdata, pubevent=True, database=True, dbforce=True)
		self.reportStatus('acquisition', 'Waiting for DriftManager to check drift...')
		self.driftimagedone.wait()
		self.driftdone.wait()
		return self.driftresult

	def reportStatus(self, type, message):
		self.logger.info('%s: %s' % (type, message))

	def simulateTarget(self):
		self.setStatus('processing')
		currentpreset = self.presetsclient.getCurrentPreset()
		if currentpreset is None:
			try:
				self.validatePresets()
			except InvalidPresetsSequence:
				self.logger.error('Configure at least one preset in the settings for this node.')
				return
			presetnames = self.settings['preset order']
			currentpreset = self.presetsclient.getPresetByName(presetnames[0])
		targetdata = self.newSimulatedTarget(preset=currentpreset,grid=self.grid)
		self.publish(targetdata, database=True)
		## change to 'processing' just like targetwatcher does
		proctargetdata = leginondata.AcquisitionImageTargetData(initializer=targetdata, status='processing')
		try:
			ret = self.processTargetData(targetdata=proctargetdata, attempt=1)
		except BadImageStatsPause, e:
			''' FIX ME!!! need to pause and allow repeat? '''
			self.logger.error('processing target failed: %s' %e)
			ret = 'aborted'
		except BadImageStatsAbort, e:
			self.logger.error('processing target failed: %s' %e)
			ret = 'aborted'
		self.logger.info('Done with simulated target, status: %s (repeat will not be honored)' % (ret,))
		self.setStatus('idle')

	def simulateTargetLoop(self):
		self.setStatus('processing')
		iterations = self.settings['iterations']
		self.logger.info('begin simulated target loop of %s iterations' % (iterations,))
		self.simloopstop.clear()
		for i in range(iterations):
			self.logger.info('iteration %s of %s' % (i+1, iterations,))
			self.simulateTarget()
			self.setStatus('processing')
			if self.simloopstop.isSet():
				self.logger.info('User stopped loop')
				break
			waittime = self.settings['wait time']
			self.setStatus('waiting')
			time.sleep(waittime)
			self.setStatus('processing')
		self.logger.info('Simulated Target Loop Done')
		self.setStatus('idle')
	

	def simulateTargetLoopStop(self):
		self.logger.info('Simulated Target Loop will stop after next iteration')
		self.simloopstop.set()

	def loadImage(self, imagedata):
			try:
				num = imagedata['image'].read()
			except AttributeError:
				pass
			else:
				imagedata.__setitem__('image', num, force=True)
			self.setImage(numpy.asarray(imagedata['image'], numpy.float32), 'Image')

	def processReferenceTarget(self,preset_name):
		refq = leginondata.ReferenceTargetData(session=self.session)
		results = refq.query(results=1, readimages=False)
		if not results:
			return
		request_data = leginondata.FixBeamData()
		request_data['session'] = self.session
		request_data['preset'] = preset_name
		self.publish(request_data, database=True, pubevent=True, wait=True)

	def getMoveTypes(self):
		movetypes = []
		for key, value in self.calclients.items():
			if value.mover:
				movetypes.append(key)
		return movetypes
	def setGrid(self,evt):
		if evt['grid'] is None:
			self.grid = None
			self.logger.info('Remove filename grid prefix')
			return
		grid = evt['grid']
		self.grid = grid
		label = gridlabeler.getGridLabel(grid)
		self.logger.info('Add grid prefix as '+label)
