#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import threading
import data
import uiserver

# Exceptions
class Error(Exception):
	pass

class ObjectError(Error):
	pass

class DataError(ObjectError):
	pass

class PermissionsError(DataError):
	pass

class PrintRLock(object):
	def __init__(self, name):
		self.name = name
		self.rlock = threading.RLock()
		self.lock = threading.Lock()
		self.acquired = 0

	def acquire(self):
		self.lock.acquire()
		thread = threading.currentThread()
		print self.acquired, self.name, 'acquiring for', thread.getName()
		self.rlock.acquire()
		print self.acquired, self.name, 'acquired for', thread.getName()
		self.acquired += 1
		self.lock.release()

	def release(self):
		self.lock.acquire()
		thread = threading.currentThread()
		self.rlock.release()
		self.acquired -= 1
		print self.acquired, self.name, 'released for', thread.getName()
		self.lock.release()

# UI Objects
class Object(object):
	typelist = ('object',)
	def __init__(self, name):
		if type(name) is not str:
			raise TypeError('name must be a string')
		self.name = name
		self.parent = None
		self.server = None
		self.configuration = {}
		self.configuration['enabled'] = True
		#self.lock = PrintRLock(self.name)
		self.lock = threading.RLock()

	def _getNameList(self):
		namelist = [self.name,]
		if self.parent is not None:
			namelist = self.parent._getNameList() + namelist
		return namelist

	def _getObjectFromList(self, namelist):
		if len(namelist) != 1 or namelist[0] != self.name:
			raise ValueError('connect get Object from list, no such Object')
		return self

	def _setServer(self, server):
		if not isinstance(server, uiserver.Server) and server is not None:
			raise TypeError('Invalid server for Object')
		self.server = server

	def _enable(self, enabled, block, thread):
		self.configuration['enabled'] = enabled
		if self.server is not None:
			self.server._configureObject(self, None, block, thread)

	def disable(self, block=True, thread=False):
		self.lock.acquire()
		self._enable(False, block, thread)
		self.lock.release()

	def enable(self, block=True, thread=False):
		self.lock.acquire()
		self._enable(True, block, thread)
		self.lock.release()

class Method(Object):
	typelist = Object.typelist + ('method',)
	def __init__(self, name, method):
		Object.__init__(self, name)
		if not callable(method):
			raise TypeError('method must be callable')
		self.method = method

class Data(Object):
	permissionsvalues = ('r', 'w', 'rw', 'wr')
	typelist = Object.typelist + ('data',)
	def __init__(self, name, value, permissions='r', callback=None,
								persist=False):
		Object.__init__(self, name)
		if permissions in self.permissionsvalues:
			if 'r' in permissions:
				self.configuration['read'] = True
			else:
				self.configuration['read'] = False
			if 'w' in permissions:
				self.configuration['write'] = True
			else:
				self.configuration['write'] = False
		else:
			raise ValueError('invalid permissions value')

		self.setCallback(callback)

		self.persist = persist

		# no callback?
		self.set(value)

	def setCallback(self, callback):
		if not callable(callback) and callback is not None:
			raise TypeError('callback must be callable or None')
		self.lock.acquire()
		self.callback = callback
		self.lock.release()

	def _set(self, value):
		self.lock.acquire()
		if self.configuration['write']:
			self.set(value)
		else:
			self.lock.release()
			raise PermissionsError('cannot set, permission denied')
		self.lock.release()

	def set(self, value, callback=True, block=True, thread=False):
		self.lock.acquire()
		if callback and self.callback is not None:
			value = self.callback(value)
		if self.validate(value):
			self.value = value
		else:
			self.lock.release()
			raise TypeError('invalid data value for type')
		if self.server is not None:
			self.server._setObject(self, None, block, thread)
		self.lock.release()

	def _get(self):
		self.lock.acquire()
		if self.configuration['read']:
			value = self.get()
		else:
			self.lock.release()
			raise PermissionsError('cannot get, permission denied')
		self.lock.release()
		return value

	def get(self):
		self.lock.acquire()
		value = self.value
		self.lock.release()
		return value

	def validate(self, value):
		#return False
		return True

class Boolean(Data):
	typelist = Data.typelist + ('boolean',)
	def validate(self, value):
		return True
		if type(value) is bool:
			return True
		else:
			return False

class Number(Data):
	typelist = Data.typelist + ('number',)
	def validate(self, value):
		return True
		if type(value) in (int, float) or value is None:
			return True
		else:
			return False

class Integer(Data):
	typelist = Data.typelist + ('integer',)
	def validate(self, value):
		return True
		if type(value) is int or value is None:
			return True
		else:
			return False

class Progress(Integer):
	typelist = Integer.typelist + ('progress',)

class Float(Data):
	typelist = Data.typelist + ('float',)
	def validate(self, value):
		return True
		if type(value) is float or value is None:
			return True
		else:
			return False

class String(Data):
	typelist = Data.typelist + ('string',)
	def validate(self, value):
		return True
		if type(value) is str or value is None:
			return True
		else:
			return False

class Array(Data):
	typelist = Data.typelist + ('array',)
	def validate(self, value):
		return True

class Sequence(Array):
	typelist = Array.typelist + ('sequence',)
	def __init__(self, name, value):
		Array.__init__(self, name, value)

class GridTray(Array):
	typelist = Array.typelist + ('grid tray',)

class Struct(Data):
	typelist = Data.typelist + ('struct',)

class Application(Struct):
	typelist = Struct.typelist + ('application',)

class Container(Object):
	typelist = Object.typelist + ('container',)
	def __init__(self, name):
		Object.__init__(self, name)
		self.uiobjectdict = {}
		self.uiobjectlist = []

	def _setServer(self, server):
		Object._setServer(self, server)
		for uiobject in self.uiobjectlist:
			uiobject._setServer(server)

	def addObject(self, uiobject, block=True, thread=False):
		self.lock.acquire()
		if uiobject.name in self.uiobjectdict:
			self.lock.release()
			raise ValueError(uiobject.name + ' name already exists in Object mapping')

		if not isinstance(uiobject, Object):
			self.lock.release()
			raise TypeError('value must be a Object instance')

		uiobject.lock.acquire()
		uiobject.parent = self
		uiobject._setServer(self.server)
		self.uiobjectdict[uiobject.name] = uiobject
		self.uiobjectlist.append(uiobject)

		if self.server is not None:
			self.server._addObject(uiobject, None, block, thread)
		uiobject.lock.release()
		self.lock.release()

	def addObjects(self, uiobjects, block=True, thread=False):
		self.lock.acquire()
		for uiobject in uiobjects:
			self.addObject(uiobject, block, thread)
		self.lock.release()

	def deleteObject(self, name, client=None, block=True, thread=False):
		self.lock.acquire()
		if name in self.uiobjectdict:
			uiobject = self.uiobjectdict[name]
			uiobject.lock.acquire()
			del self.uiobjectdict[name]
			self.uiobjectlist.remove(uiobject)
			if self.server is not None:
				self.server._deleteObject(uiobject, client, block, thread)
			uiobject.server = None
			uiobject.parent = None
			uiobject.lock.release()
		else:
			self.lock.release()
			raise ValueError('cannot delete Object, not in Object mapping')
		self.lock.release()

	def _getObjectFromList(self, namelist):
		if type(namelist) not in (list, tuple):
			raise TypeError('name hierarchy must be a list')

		if not namelist:
			raise ValueError('no widget name[s] specified')

		if namelist[0] != self.name:
			raise ValueError('cannot get object from list, not parent of Object')

		if len(namelist) == 1:
			return self
		else:
			for uiobject in self.uiobjectlist:
				try:
					obj = uiobject._getObjectFromList(namelist[1:])
					return obj
				except ValueError:
					pass
			raise ValueError('cannot get object, not in child Object mappings')

class SmallContainer(Container):
	typelist = Container.typelist + ('small',)

class MediumContainer(Container):
	typelist = Container.typelist + ('medium',)

class LargeContainer(Container):
	typelist = Container.typelist + ('large',)

class ExternalContainer(Container):
	typelist = Container.typelist + ('external',)

def clientContainerFactory(containerclass):
	class ClientContainer(containerclass):
		typelist = containerclass.typelist + ('client',)
		def __init__(self, name, location):
			self.value = location
			containerclass.__init__(self, name)
	return ClientContainer

SmallClientContainer = clientContainerFactory(SmallContainer)
MediumClientContainer = clientContainerFactory(MediumContainer)
LargeClientContainer = clientContainerFactory(LargeContainer)

class SelectFromList(Container):
	typelist = Container.typelist + ('select from list',)
	selectclass = Array
	def __init__(self, name, listvalue, selected, permissions='r',
								callback=None, persist=False):
		Container.__init__(self, name)
		self.list = Array('List', listvalue, permissions, persist=persist)
		self.selected = self.selectclass('Selected', selected, 'rw', callback,
																			persist=persist)
		self.persist = persist
		self.addObject(self.list)
		self.addObject(self.selected)

	def setCallback(self, callback):
		self.selected.setCallback(callback)

	def set(self, listvalue, selected):
		self.setList(listvalue)
		self.setSelected(selected)

	def getList(self):
		return self.list.get()

	def setList(self, listvalue):
		self.list.set(listvalue)

	def getSelected(self):
		return self.selected.get()

	def setSelected(self, selected):
		self.selected.set(selected)

	def getSelectedValues(self, selected=None):
		values = []
		valuelist = self.getList()
		if selected is None:
			selected = self.getSelected()
		for i in selected:
			try:
				values.append(valuelist[i])
			except IndexError:
				raise RuntimeError('selected index out of range')
		return values

class SingleSelectFromList(SelectFromList):
	typelist = SelectFromList.typelist + ('single',)
	selectclass = Integer
	def __init__(self, name, listvalue, selected, permissions='r',
								callback=None, persist=False):
		SelectFromList.__init__(self, name, listvalue, selected, permissions,
														callback, persist)

	def getSelectedValue(self, selected=None):
		if selected is None:
			selected = self.getSelected()
		values = self.getSelectedValues([selected])
		try:
			return values[0]
		except IndexError:
			return None

class SelectFromStruct(Container):
	typelist = Container.typelist + ('select from struct',)
	# callback
	def __init__(self, name, structvalue, selectedvalue, permissions='r',
								persist=False):
		Container.__init__(self, name)
		self.struct = Struct('Struct', structvalue, permissions, persist=persist)
		self.selected = Array('Selected', selectedvalue, 'rw', persist=persist)
		self.persist = persist
		self.addObject(self.struct)
		self.addObject(self.selected)

	def set(self, structvalue, selectedvalue):
		self.setStruct(structvalue)
		self.setSelected(selectedvalue)

	def getStruct(self):
		return self.struct.get()

	def setStruct(self, structvalue):
		self.struct.set(structvalue)

	def getSelected(self):
		return self.selected.get()

	def setSelected(self, selectedvalue):
		self.selected.set(selectedvalue)

class Message(Container):
	typelist = Container.typelist + ('message',)
	def __init__(self, name, type, message):
		Container.__init__(self, name)
		self.addObject(String('Type', type, 'r'))
		self.addObject(String('Message', message, 'r'))
		self.addObject(Method('Clear', self.clear))

	def destroy(self):
		try:
			self.parent.deleteObject(self.name)
		except ValueError:
			pass

	def clear(self):
		self.destroy()

class MessageLog(Container):
	typelist = Container.typelist + ('message log',)
	def __init__(self, name):
		self.counter = 0
		Container.__init__(self, name)

	def addObject(self, uiobject, block=True, thread=False):
		if not isinstance(uiobject, Message):
			raise TypeError
		Container.addObject(self, uiobject, block, thread)

	def message(self, type, message):
		self.addObject(Message('Message #%d' % self.counter, type, message))
		self.counter += 1

	def information(self, message):
		self.message('info', message)

	def warning(self, message):
		self.message('warning', message)

	def error(self, message):
		self.message('error', message)

class Dialog(ExternalContainer):
	typelist = ExternalContainer.typelist + ('dialog',)
	def __init__(self, name):
		ExternalContainer.__init__(self, name)

	def destroy(self):
		try:
			self.parent.deleteObject(self.name)
		except ValueError:
			pass

class MessageDialog(Dialog):
	typelist = Dialog.typelist + ('message',)
	def __init__(self, name, label):
		Dialog.__init__(self, name)
		self.addObject(String('Message', label, 'r'))
		self.addObject(Method('OK', self.ok))

	def ok(self):
		self.destroy()

class FileDialog(Dialog):
	typelist = Dialog.typelist + ('file',)
	oklabel = 'OK'
	def __init__(self, name, callback):
		Dialog.__init__(self, name)
		self.callback = callback
		self.filename = String('Filename', '', 'rw')
		self.addObjects((self.filename, Method(self.oklabel, self.ok),
																		Method('Cancel', self.cancel)))

	def ok(self):
		self.callback(self.filename.get())
		self.destroy()

	def cancel(self):
		self.callback(None)
		self.destroy()

class SaveFileDialog(FileDialog):
	typelist = FileDialog.typelist + ('save',)
	oklabel = 'Save'

class LoadFileDialog(FileDialog):
	typelist = FileDialog.typelist + ('load',)
	oklabel = 'Load'

class Binary(Data):
	typelist = Data.typelist + ('binary',)

class PILImage(Binary):
	typelist = Binary.typelist + ('PIL image',)

class Image(Binary):
	typelist = Binary.typelist + ('image',)

class ClickImage(Container):
	typelist = Container.typelist + ('click image',)
	def __init__(self, name, clickcallback, image, permissions='r',
								persist=False):
		self.clickcallback = clickcallback
		Container.__init__(self, name)
		self.image = Image('Image', image, 'r', persist=persist)
		self.coordinates = Array('Coordinates', [], 'rw', persist=persist)
		self.method = Method('Click', self.doClickCallback)
		self.persist = persist
		self.addObject(self.coordinates)
		self.addObject(self.method)
		self.addObject(self.image)

	def setImage(self, value):
		self.image.set(value)

	def doClickCallback(self):
		self.clickcallback(tuple(self.coordinates.get()))

class TargetImage(Container):
	typelist = Container.typelist + ('target image',)
	# callback
	def __init__(self, name, image, permissions='r', persist=False):
		Container.__init__(self, name)
		self.targets = {}
		self.image = Image('Image', image, 'r', persist=persist)
		self.persist = persist
		self.addObject(self.image)

	def addTargetType(self, name, targets=[]):
		if name in self.targets:
			raise ValueError('Target type already exists')
		self.targets[name] = Array(name, targets, 'rw')
		self.addObject(self.targets[name])

	def deleteTargetType(self, name):
		try:
			self.deleteObject(self.targets[name])
			del self.targets[name]
		except KeyError:
			raise ValueError('No such target type')

	def getTargetType(self, name):
		try:
			return self.targets[name].get()
		except KeyError:
			raise ValueError('No such target type')

	def setTargetType(self, name, value):
		try:
			self.targets[name].set(value)
		except KeyError:
			raise ValueError('No such target type')

	def setTargets(self, value):
		for targetarray in self.targets.values():
			targetarray.set(value)

	def getTargets(self):
		value = {}
		for name in self.targets:
			value[name] = self.targets[name].get()
		return value

	def setImage(self, value):
		self.image.set(value)

class ResearchWidget(Container):
	typelist = Container.typelist + ('research',)
	def __init__(self, name, noderesearch, datatype, fields={}):
		Container.__init__(self, name)
		self.noderesearch = noderesearch
		self.datatype = datatype

		self.datalist = Struct('Data', {}, 'r')
		self.researchmethod = Method('Research', self.research)
		self.addObject(self.datalist)
		self.addObject(self.researchmethod)

	def research(self):
		datainstances = self.noderesearch(dataclass=self.datatype)
		self.datalist.set(self.datalistFromDataInstances(datainstances))

	def datalistFromDataInstances(self, datainstances):
		ids = {}
		for typemap in self.datatype.typemap():
			if not issubclass(typemap[1], data.Data):
				values = []
				for datainstance in datainstances:
					value = datainstance[typemap[0]]
					if value is None:
						value = str(value)
					values.append(value)
				ids[typemap[0]] = values
		return ids

