#!/usr/bin/env python

#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import leginonconfig
import leginonobject
import Numeric
import strictdict
import warnings
import types
import threading
import dbdatakeeper
import copy
import tcptransport

class DataError(Exception):
	pass
class DataManagerOverflowError(DataError):
	pass
class DataAccessError(DataError):
	pass

## manages weak references between data instances
## DataManager holds strong references to every Data instance that
## is created.  The memory size is restricted such that the first instances
## to be created are the first to be deleted from DataManager.
class DataManager(object):
	def __init__(self):
		## will connect to database before first query
		self.db = None

		## start server
		if 1:
			self.startServer()
		else:
			self.location = (None, None)

		## the size of these dicts are maintained by size restriction
		self.datadict = strictdict.OrderedDict()
		self.sizedict = {}
		self.db2dm = {}
		self.dm2db = {}

		megs = 256
		self.maxsize = megs * 1024 * 1024
		self.dmid = 0
		self.size = 0
		self.lock = threading.RLock()

	def startServer(self):
		self.server = tcptransport.Server(self)
		port = self.server.port
		hostname = self.server.hostname
		self.location = (hostname, port)
		print 'LOCATION', self.location

	def newid(self):
		self.dmid += 1
		return (self.location, self.dmid)

	def insert(self, datainstance):
		self.lock.acquire()
		try:
			## insert into datadict and sizedict
			newid = self.newid()
			self.datadict[newid] = datainstance
			datainstance.dmid = newid
			self.resize(datainstance)

			## insert into persist dicts if it is in database
			if datainstance.dbid is not None:
				self.setPersistent(datainstance)
		finally:
			self.lock.release()

	def setPersistent(self, datainstance):
		self.lock.acquire()
		try:
			dataclass = datainstance.__class__
			dbid = datainstance.dbid
			if dbid is None:
				raise DataError('persist can only be called on data that is stored in the database')
			dmid = datainstance.dmid
			self.dm2db[dmid] = dataclass,dbid
			self.db2dm[dataclass,dbid] = dmid
		finally:
			self.lock.release()

	def remove(self, dmid):
		self.lock.acquire()
		try:
			del self.datadict[dmid]
			self.size -= self.sizedict[dmid]
			del self.sizedict[dmid]
			print '****removed something', self.size
			if dmid in self.dm2db:
				dbkey = self.dm2db[dmid]
				del self.db2dm[dbkey]
				del self.dm2db[dmid]
		finally:
			self.lock.release()

	def resize(self, datainstance):
		self.lock.acquire()
		try:
			dsize = datainstance.size()
			if dsize > self.maxsize:
				raise DataManagerOverflowError('new size is too big for DataManager')
			## check previous size
			dmid = datainstance.dmid
			if dmid in self.sizedict:
				oldsize = self.sizedict[dmid]
			else:
				oldsize = 0
			self.size -= oldsize
			self.size += dsize
			self.sizedict[dmid] = dsize
			self.clean()
		finally:
			self.lock.release()

	def clean(self):
		self.lock.acquire()
		try:
			while self.size > self.maxsize:
				first = self.datadict.keys()[0]
				self.remove(first)
		finally:
			self.lock.release()

	def getDataFromDB(self, dataclass, dbid):
		if self.db is None:
			self.db = dbdatakeeper.DBDataKeeper()
		return self.db.direct_query(dataclass, dbid)

	def getRemoteData(self, datareference):
		dmid = datareference.dmid
		location = {'hostname': dmid[0][0], 'port': dmid[0][1]}
		client = tcptransport.Client(location)
		datainstance = client.pull(datareference)
		return datainstance

	def getData(self, datareference):
		self.lock.acquire()
		try:
			dataclass = datareference.dataclass
			datainstance = None
			dmid = datareference.dmid
			dbid = datareference.dbid

			## maybe data instance has been reborn from DB
			## since DataReference object was created
			if (dataclass,dbid) in self.db2dm:
				dmid = self.db2dm[dataclass,dbid]
				datareference.dmid = dmid

			### check if this is a remote data reference
			location = self.location
			if dmid is not None:
				location = dmid[0]

			## now find the data
			if location != self.location:
				## in remote memory
				datainstance = self.getRemoteData(datareference)
			if dmid in self.datadict:
				## in local memory
				datainstance = self.datadict[dmid]
				# access to datadict causes move to front
				del self.datadict[dmid]
				self.datadict[dmid] = datainstance
			elif dbid is not None:
				## in database
				datainstance = self.getDataFromDB(dataclass, dbid)
				if datainstance is not None:
					dmid = datainstance.dmid
			if datainstance is None:
				raise DataAccessError('Referenced data no longer exists')
		finally:
			self.lock.release()
		return datainstance

	def query(self, datareference):
		### this is how tcptransport server accesses this data manager
		return self.getData(datareference)

datamanager = DataManager()

class DataReference(object):
	'''
	initialized with a datainstance or 
	a dataclass and at least one of dmid and/or dbid
	'''
	def __init__(self, datainstance=None, dataclass=None, dmid=None, dbid=None):
		if datainstance is not None:
			self.dataclass = datainstance.__class__
			self.dmid = datainstance.dmid
			self.dbid = datainstance.dbid
		elif dataclass is not None:
			self.dataclass = dataclass
			if dmid is None and dbid is None:
				raise DataError('DataReference has neither a dmid nor a dbid')
			self.dmid = dmid
			self.dbid = dbid
		else:
			raise DataError('DataReference needs either datainstance or dataclass')

	def getData(self):
		datainstance = datamanager.getData(self)
		if datainstance is not None:
			self.dmid = datainstance.dmid
			self.dbid = datainstance.dbid
		return datainstance

## Unresolved issue:
##  It would be nice if you could cast one Data type to another
##  Right now that will probably result in a key error


class DataDict(strictdict.TypedDict):
	'''
	A wrapper around TypedDict that adds a class method: typemap()
	This class method is used to create the type_map_or_seq argument
	that is normally passed during instantiation.  We then remove this
	argument from the init method.  In other words,
	we are hard coding the TypedDict types into the class and making
	it easy to override these types in a subclass.

	The typemap() method should return the same information as the 
	types() method already provided by TypedDict.  The difference is
	that (as of now) types() returns a KeyedDict and typedict() 
	returns a list of tuples mapping.  Maybe this can be unified soon.
	Another key difference is that since typemap() is a class method,
	we can inquire about the types of a DataDict's contents without
	actually having an instance.  This might be useful for something
	like a database interface that needs to create tables from these
	classes.
	'''
	def __init__(self, map_or_seq=None):
		strictdict.TypedDict.__init__(self, map_or_seq, type_map_or_seq=self.typemap())

	def typemap(cls):
		'''
		Returns the mapping of keys to types for this class.
		  [(key, type), (key, type), ...]
		Override this in subclasses to specialize the contents
		of this type of data.
		'''
		return []
	typemap = classmethod(typemap)

	def getFactory(self, valuetype):
		if valuetype is DataDict:
			f = valuetype
		else:
			f = strictdict.TypedDict.getFactory(self, valuetype)
		return f

class UnknownData(object):
	'''
	this is a place holder for a Data instance that is not yet known
	'''
	def __init__(self, qikey):
		self.qikey = qikey

def accumulateData(originaldata, func, memo=None):
	d = id(originaldata)

	if memo is None:
		memo = {}
	if memo.has_key(d):
		return None

	myresult = []
	for key,value in originaldata.items():
		if isinstance(value, Data):
			childresult = accumulateData(value, func, memo)
			if childresult is not None:
				myresult += childresult

	myresult = func(originaldata) + myresult

	memo[d] = myresult
	return myresult

def data2dict(idata, noNone=False):
	d = {}
	for key,value in idata.items():
		if isinstance(value, Data):
			subd = data2dict(value, noNone)
			if subd:
				d[key] = subd
		else:
			if not noNone or value is not None:
				d[key] = value
	return d

class Data(DataDict, leginonobject.LeginonObject):
	'''
	Combines DataDict and LeginonObject to create the base class
	for all leginon data.  This can be initialized with keyword args
	as long as those keys are declared in the specific subclass of
	Data.  The special keyword 'initializer' can also be used
	to initialize with a dictionary.  If a key exists in both
	initializer and kwargs, the kwargs value is used.
	'''
	def __init__(self, **kwargs):
		DataDict.__init__(self)

		## Database ID (primary key)
		## If this is None, then this data has not
		## been inserted into the database
		self.dbid = None

		## DataManager ID
		## this is None, then this data has not
		## been inserted into the DataManager
		self.dmid = None

		datamanager.insert(self)

		# if initializer was given, update my values
		if 'initializer' in kwargs:
			self.update(kwargs['initializer'])
			del kwargs['initializer']

		# additional keyword arguments also update my values
		# (overriding anything set by initializer)
		self.update(kwargs)

		# LeginonObject base class needs id
		legid = self['id']
		leginonobject.LeginonObject.__init__(self, legid)

	def setPersistent(self, dbid):
		self.dbid = dbid
		datamanager.setPersistent(self)

	def items(self, dereference=True):
		original = super(Data, self).items()
		if not dereference:
			return original
		deref = []
		for item in original:
			if isinstance(item[1], DataReference):
				val = item[1].getData()
			else:
				val = item[1]
			deref.append((item[0],val))
		return deref

	def __getstate__(self):
		return self.__dict__

	def values(self, dereference=True):
		original = super(Data, self).values()
		if not dereference:
			return original
		deref = []
		for value in original:
			if isinstance(value, DataReference):
				val = value.getData()
			else:
				val = value
			deref.append(val)
		return deref

	def special_getitem(self, key, dereference):
		'''
		'''
		value = super(Data, self).__getitem__(key)
		if dereference and isinstance(value, DataReference):
			value = value.getData()
		return value

	def __getitem__(self, key):
		return self.special_getitem(key, dereference=True)

	def __setitem__(self, key, value):
		'''
		'''
		super(Data, self).__setitem__(key, value)
		if not hasattr(self, 'initdone'):
			return

		if hasattr(self, 'dbid') and self.dbid is not None:
			raise RuntimeError('persistent data cannot be modified, try to create a new instance instead, or use toDict() if a dict representation will do')
		### synch with leginonobject attributes
		if key == 'id':
			super(Data, self).__setattr__(key, value)
		### removed the stuff about setting session attribute
		### it is really is necessary, we should 
		elif isinstance(value,Data):
			value = DataReference(value)
		#DataDict.__setitem__(self, key, value)
		#super(Data, self).__setitem__(key, value)
		datamanager.resize(self)

	def typemap(cls):
		t = DataDict.typemap()
		t += [('id', tuple)]
		return t
	typemap = classmethod(typemap)

	def getFactory(self, valuetype):
		try:
			mine = issubclass(valuetype, Data)
		except TypeError:
			mine = False

		if mine:
			def f(value):
				if isinstance(value, DataReference):
					if valuetype is value.dataclass:
						return value
					else:
						print 'VALUETYPE', valuetype, value.dataclass
						raise ValueError('must by type %s' (valuetype,))
				if isinstance(value, valuetype):
					return value
				elif isinstance(value, UnknownData):
					return value
				else:
					raise ValueError('must be type %s' % (valuetype,))
				
		else:
			f = DataDict.getFactory(self, valuetype)
		return f

	def toDict(self, noNone=False):
		return data2dict(self, noNone)

	def size(self):
		size = 0
		for key, datatype in self.types().items():
			try:
				isdata = issubclass(datatype, Data)
			except TypeError:
				isdata = False
			if isdata:
				## do not include size of other Data
				## and even if you do, self[key]
				## is dereferencing and possibly querying
				## the database
				continue
			if self[key] is not None:
				size += self.sizeof(self[key])
		return size

	def sizeof(self, value):
		if type(value) is Numeric.ArrayType:
			size = reduce(Numeric.multiply, value.shape) * value.itemsize()
		elif value is None:
			size = 0
		else:
			## this is my stupid estimate of size for other objects
			size = 8

		return size


'''
## How to define a new leginon data type:
##   - Inherit Data or a subclass of Data.
##   - do not overload the __init__ method (unless you have a good reason)
##   - Override the typemap(cls) class method
##   - make sure typemap is defined as a classmethod:
##      typemap = classmethod(typemap)
##   - typemap() should return a sequence mapping, usually a list
##       of tuples:   [ (key, type), (key, type),... ]
## Examples:
class NewData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [ ('stuff', int), ('thing', float), ]
		return t
	typemap = classmethod(typemap)

class OtherData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [ ('newdata', NewData), ('mynum', int),]
		return t
	typemap = classmethod(typemap)

class MoreData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [ ('newdata1', NewData), ('newdata2', NewData), ('otherdata', OtherData),]
		return t
	typemap = classmethod(typemap)

'''

class GroupData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('name', str),
					('description', str)]
		return t
	typemap = classmethod(typemap)
	
class UserData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('name', str),
					('full name', str),
					('group', GroupData)]
		return t
	typemap = classmethod(typemap)

class InstrumentData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('name', str),
					('description', str),
					('scope', str),
					('camera', str),
					('hostname', str),
					('camera size', int),
					('camera pixel size', float)]
		return t
	typemap = classmethod(typemap)

class SessionData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('name', str),
					('user', UserData),
					('instrument', InstrumentData),
					('image path', str),
					('comment', str)]
		return t
	typemap = classmethod(typemap)

class InSessionData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('session', SessionData)]
		return t
	typemap = classmethod(typemap)

class EMData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [ ('system time', float)]
		return t
	typemap = classmethod(typemap)

scope_params = [
	('magnification', int),
	('spot size', int),
	('intensity', float),
	('image shift', dict),
	('beam shift', dict),
	('defocus', float),
	('focus', float),
	('reset defocus', int),
	('screen current', float), 
	('beam blank', str), 
	('stigmator', dict),
	('beam tilt', dict),
	('corrected stage position', int),
	('stage position', dict),
	('holder type', str),
	('holder status', str),
	('stage status', str),
	('vacuum status', str),
	('column valves', str),
	('column pressure', float),
	('turbo pump', str),
	('high tension', int),
	('main screen position', str),
	('small screen position', str),
	('low dose', str),
	('low dose mode', str),
	('film stock', int),
	('film exposure number', int),
	('film exposure', bool),
	('film exposure type', str),
	('film exposure time', float),
	('film manual exposure time', float),
	('film automatic exposure time', float),
	('film text', str),
	('film user code', str),
	('film date type', str),
]
camera_params = [
	('dimension', dict),
	('binning', dict),
	('offset', dict),
	('exposure time', float),
	('exposure type', str),
	('image data', strictdict.NumericArrayType),
	('inserted', bool)
]

class ScopeEMData(EMData):
	def typemap(cls):
		t = EMData.typemap()
		t += scope_params
		return t
	typemap = classmethod(typemap)

class CameraEMData(EMData):
	def typemap(cls):
		t = EMData.typemap()
		t += camera_params
		return t
	typemap = classmethod(typemap)

class AllEMData(EMData):
	'''
	this includes everything from scope and camera
	'''
	def typemap(cls):
		t = EMData.typemap()
		t += scope_params
		t += camera_params
		return t
	typemap = classmethod(typemap)

class CameraConfigData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('dimension', dict),
			('binning', dict),
			('offset', dict),
			('exposure time', float),
			('exposure type', str),
			('correct', int),
			('auto square', int),
			('auto offset', int),
		]
		return t
	typemap = classmethod(typemap)

class LocationData(InSessionData):
	pass

class NodeLocationData(LocationData):
	def typemap(cls):
		t = LocationData.typemap()
		t += [ ('location', dict), ]
		t += [ ('class string', str), ]
		return t
	typemap = classmethod(typemap)

class DataLocationData(LocationData):
	def typemap(cls):
		t = LocationData.typemap()
		t += [ ('location', list), ]
		return t
	typemap = classmethod(typemap)

class NodeClassesData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [ ('nodeclasses', tuple), ]
		return t
	typemap = classmethod(typemap)

class DriftData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
		  ('rows', float),
		  ('cols', float),
		  ('rowmeters', float),
		  ('colmeters', float),
		  ('interval', float),
		]
		return t
	typemap = classmethod(typemap)

class CalibrationData(InSessionData):
	pass

class CameraSensitivityCalibrationData(CalibrationData):
	def typemap(cls):
		t = CalibrationData.typemap()
		t += [
			('high tension', int),
			('sensitivity', int),
		]
		return t
	typemap = classmethod(typemap)

class MagDependentCalibrationData(CalibrationData):
	def typemap(cls):
		t = CalibrationData.typemap()
		t += [
			('magnification', int),
			('high tension', int),
		]
		return t
	typemap = classmethod(typemap)

class PixelSizeCalibrationData(MagDependentCalibrationData):
	def typemap(cls):
		t = MagDependentCalibrationData.typemap()
		t += [ ('pixelsize', float), ('comment', str)]
		return t
	typemap = classmethod(typemap)

class EucentricFocusData(MagDependentCalibrationData):
	def typemap(cls):
		t = MagDependentCalibrationData.typemap()
		t += [ ('focus', float)]
		return t
	typemap = classmethod(typemap)

class MatrixCalibrationData(MagDependentCalibrationData):
	def typemap(cls):
		t = MagDependentCalibrationData.typemap()
		t += [ ('type', str), ('matrix', strictdict.NumericArrayType), ]
		return t
	typemap = classmethod(typemap)

class MoveTestData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('move pixels x', float),
			('move pixels y', float),
			('move meters x', float),
			('move meters y', float),
			('error pixels x', float),
			('error pixels y', float),
			('error meters x', float),
			('error meters y', float),
		]
		return t
	typemap = classmethod(typemap)

class MatrixMoveTestData(MoveTestData):
	def typemap(cls):
		t = MoveTestData.typemap()
		t += [
			('calibration', MatrixCalibrationData),
		]
	typemap = classmethod(typemap)

class ModeledStageMoveTestData(MoveTestData):
	def typemap(cls):
		t = MoveTestData.typemap()
		t += [
			('model', StageModelCalibrationData),
			('mag only', StageModelMagCalibrationData),
		]
	typemap = classmethod(typemap)

class StageModelCalibrationData(CalibrationData):
	def typemap(cls):
		t = CalibrationData.typemap()
		t += [
			('label', str),
			('axis', str),
			('period', float),
			('a', strictdict.NumericArrayType),
			('b', strictdict.NumericArrayType)
		]
		return t
	typemap = classmethod(typemap)

class StageModelMagCalibrationData(MagDependentCalibrationData):
	def typemap(cls):
		t = MagDependentCalibrationData.typemap()
		t += [ ('label', str), ('axis', str), ('angle', float), ('mean',float)]
		return t
	typemap = classmethod(typemap)

class StageMeasurementData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('label', str),
			('high tension', int),
			('magnification', int),
			('axis', str),
			('x',float),
			('y',float),
			('delta',float),
			('imagex',float),
			('imagey',float),
		]
		return t
	typemap = classmethod(typemap)

class PresetData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('name', str),
			('magnification', int),
			('spot size', int),
			('intensity', float),
			('image shift', dict),
			('beam shift', dict),
			('defocus', float),
			('dimension', dict),
			('binning', dict),
			('offset', dict),
			('exposure time', int),
			('removed', int),
			('hasref', bool),
			('dose', float),
		]
		return t
	typemap = classmethod(typemap)

class NewPresetData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('name', str),
			('magnification', int),
			('spot size', int),
			('intensity', float),
			('image shift', dict),
			('beam shift', dict),
			('defocus', float),
			('dimension', dict),
			('binning', dict),
			('offset', dict),
			('exposure time', float),
		]
		return t
	typemap = classmethod(typemap)

class PresetSequenceData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('sequence', list)
		]
		return t
	typemap = classmethod(typemap)

class CorrelationData(InSessionData):
	pass

class ImageData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('image', strictdict.NumericArrayType),
			('label', str),
			('filename', str),
		]
		return t
	typemap = classmethod(typemap)

	def path(self):
		'''
		create a directory for this image file if it does not exist.
		return the full path of this directory.
		'''
		impath = self['session']['image path']
		impath = leginonconfig.mapPath(impath)
		leginonconfig.mkdirs(impath)
		return impath

	def filename(self):
		'''
		create a unique filename for this image
		filename format:  [session]_[label]_[nodename]_[integer].mrc
		'''
		basename = self['session']['name']
		## use label if available, else use node name
		if self['label'] is not None:
			basename += '_%s' % (self['label'],)
		else:
			basename += '_%s' % (self['id'][-2],)
			
		myindex = self['id'][-1]
		basename += '_%06d.mrc' % (myindex,)
		return basename

	def thumb_filename(self):
		regular = self.filename()
		thumb = 'thumb_' + regular
		return thumb

class MosaicImageData(ImageData):
	'''Image of a mosaic'''
	def typemap(cls):
		t = ImageData.typemap()
		t += [ ('mosaic', MosaicData), ]
		t += [ ('scale', float), ]
		return t
	typemap = classmethod(typemap)

class CorrelationImageData(ImageData):
	'''
	ImageData that results from a correlation of two images
	content has the following keys:
		'image': Numeric data	
		'subject1':  first image (data id) used in correlation
		'subject2':  second image (data id) used in correlation
	'''
	def typemap(cls):
		t = ImageData.typemap()
		t += [ ('subject1', ImageData), ('subject2', ImageData), ]
		return t
	typemap = classmethod(typemap)

class CrossCorrelationImageData(CorrelationImageData):
	pass

class PhaseCorrelationImageData(CorrelationImageData):
	pass

class CameraImageData(ImageData):
	def typemap(cls):
		t = ImageData.typemap()
		t += [ ('scope', ScopeEMData), ('camera', CameraEMData), ]
		t += [('grid', GridData)]
		return t
	typemap = classmethod(typemap)


## the camstate key is redundant (it's a subset of 'camera')
## but for now it helps to query the same way we used to
class CorrectorImageData(ImageData):
	def typemap(cls):
		t = ImageData.typemap()
		t += [ ('camstate', CorrectorCamstateData), ]
		return t
	typemap = classmethod(typemap)

class DarkImageData(CorrectorImageData):
	pass

class BrightImageData(CorrectorImageData):
	pass

class NormImageData(CorrectorImageData):
	pass

class MosaicData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('data IDs', list),
		]
		return t
	typemap = classmethod(typemap)

class StageLocationData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('removed', bool),
			('name', str),
			('comment', str),
			('x', float),
			('y', float),
			('z', float),
			('a', float),
			('xy only', bool),
		]
		return t
	typemap = classmethod(typemap)

class PresetImageData(CameraImageData):
	'''
	If an image was acquire using a certain preset, use this class
	to include the preset with it.
	'''
	def typemap(cls):
		t = CameraImageData.typemap()
		t += [ ('preset', PresetData), ]
		return t
	typemap = classmethod(typemap)

class PresetReferenceImageData(PresetImageData):
	'''
	This is a reference image for getting stats at different presets
	'''
	pass

class AcquisitionImageData(PresetImageData):
	def typemap(cls):
		t = PresetImageData.typemap()
		t += [ ('target', AcquisitionImageTargetData), ]
		return t
	typemap = classmethod(typemap)

	def filename(self):
		if not self['filename']:
			raise RuntimeError('no filename set for this image')
		return self['filename'] + '.mrc'

class ProcessedAcquisitionImageData(ImageData):
	'''image that results from processing an AcquisitionImageData'''
	def typemap(cls):
		t = ImageData.typemap()
		t += [ ('source', AcquisitionImageData), ]
		return t
	typemap = classmethod(typemap)

	def filename(self):
		if not self['filename']:
			raise RuntimeError('no filename set for this image')
		return self['filename'] + '.mrc'

class AcquisitionFFTData(ProcessedAcquisitionImageData):
	'''Power Spectrum of AcquisitionImageData'''
	pass

class ScaledAcquisitionImageData(ImageData):
	'''Small version of AcquisitionImageData'''
	pass

class TrialImageData(PresetImageData):
	pass

class ImageListData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [ ('images', list), ]
		return t
	typemap = classmethod(typemap)

class AcquisitionImageListData(ImageListData):
	pass

class CorrectorPlanData(InSessionData):
	'''
	mosaic data contains data ID of images mapped to their 
	position and state.
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('camstate', CorrectorCamstateData),
			('bad_rows', tuple),
			('bad_cols', tuple),
			('clip_limits', tuple)
		]
		return t
	typemap = classmethod(typemap)

class CorrectorCamstateData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('dimension', dict),
			('binning', dict),
			('offset', dict),
		]
		return t
	typemap = classmethod(typemap)

class MosaicTargetData(InSessionData):
	'''
	this is an alias for an AcquisitionImageTargetData which is used
	to show a target in a full mosaic image
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
		  ('row', int),
		  ('column', int),
		  ('target', AcquisitionImageTargetData),
		]
		return t
	typemap = classmethod(typemap)

class GridData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('grid ID', int)]
		return t
	typemap = classmethod(typemap)

class ImageTargetData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			# pixel delta to target from state in row, column
		  ('delta row', int),
		  ('delta column', int),
		  ('scope', ScopeEMData),
		  ('camera', CameraEMData),
		  ('preset', PresetData),
		  ('type', str),
		  ('version', int),
		  ('number', int),
		  ('status', str),
			('grid', GridData),
		]
		return t
	typemap = classmethod(typemap)

class ImageTargetShiftData(InSessionData):
	'''
	This keeps a dict of target shifts for a set of images.
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			('shifts', dict),
			('requested', bool),
		]
		return t
	typemap = classmethod(typemap)

class AcquisitionImageTargetData(ImageTargetData):
	def typemap(cls):
		t = ImageTargetData.typemap()
		t += [
		  ('image', AcquisitionImageData),
		  ## this could be generalized as total dose, from all
		  ## exposures on this target.  For now, this is just to
		  ## keep track of when we have done the melt ice thing.
		  ('pre_exposure', bool),
		]
		return t
	typemap = classmethod(typemap)

### XXX the list here has variable length
class ImageTargetListData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [ ('targets', list), ]
		return t
	typemap = classmethod(typemap)

class FocuserResultData(InSessionData):
	'''
	results of doing autofocus
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
		  ('target', AcquisitionImageTargetData),
		  ('defocus', float),
		  ('stigx', float),
		  ('stigy', float),
		  ('min', float),
		  ('stig correction', int),
		  ('defocus correction', str),
		  ('pre manual check', bool),
		  ('post manual check', bool),
		  ('auto measured', bool),
		  ('auto status', str),
		]
		return t
	typemap = classmethod(typemap)

class EMTargetData(InSessionData):
	'''
	This is an ImageTargetData with deltas converted to new scope
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
			# pixel delta to target from state in row, column
		  ('scope', ScopeEMData),
		  ('preset', PresetData)
		]
		return t
	typemap = classmethod(typemap)

class ApplicationData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('name', str),
					('version', int)]
		return t
	typemap = classmethod(typemap)

class NodeSpecData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('class string', str),
					('alias', str),
					('launcher alias', str),
					('args', list),
					('new process flag', int),
					('dependencies', list),
					('application', ApplicationData)]
		return t
	typemap = classmethod(typemap)

class BindingSpecData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('event class string', str),
					('from node alias', str),
					('to node alias', str),
					('application', ApplicationData)]
		return t
	typemap = classmethod(typemap)

class DeviceGetData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('keys', list)]
		return t
	typemap = classmethod(typemap)

class DeviceData(Data):
	def typemap(cls):
		t = Data.typemap()
		return t
	typemap = classmethod(typemap)

# for testing
class DiaryData(InSessionData):
	'''
	User's diary entry
	'''
	def typemap(cls):
		t = InSessionData.typemap()
		t += [
		  ('message', str),
		]
		return t
	typemap = classmethod(typemap)

class UIData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [('object', tuple),
			('value', strictdict.AnyObject)]
		return t
	typemap = classmethod(typemap)

class ImageStatData(InSessionData):
	def typemap(cls):
		t = InSessionData.typemap()
		t += [('nx', int),
					('ny', int),
					('nz', int),
					('mode', int),
					('amin', float),
					('amax', float),
					('amean', float),
					('stdev', float),
					('image', AcquisitionImageData)]
		return t
	typemap = classmethod(typemap)


########## for testing

# new class of data
class MyData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('other', MyOtherData)]
		return t
	typemap = classmethod(typemap)

class MyOtherData(Data):
	def typemap(cls):
		t = Data.typemap()
		t += [('stuff', int)]
		t += [('encore', str)]
		return t
	typemap = classmethod(typemap)
