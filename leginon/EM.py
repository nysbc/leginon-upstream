import node
import datahandler
import scopedict
import cameradict
import threading
import data
import event
import sys
import imp
import cPickle
import dbdatakeeper
import strictdict
import copy
import time
import uidata
import Queue

if sys.platform == 'win32':
	import pythoncom

#class DataHandler(datahandler.DataBinder):
class DataHandler(node.DataHandler):
	def query(self, id):

		self.EMnode.statelock.acquire()
		done_event = threading.Event()
		self.EMnode.queue.put(Request(done_event, [id[0]]))
		done_event.wait()
		stuff = self.EMnode.state

		if emkey == 'scope':
			result = data.ScopeEMData(self.ID(), initializer=stuff)
		elif emkey == 'camera':
			result = data.CameraEMData(self.ID(), initializer=stuff)
		elif emkey == 'all':
			result = data.AllEMData(self.ID(), initializer=stuff)
		else:
			### could be either CameraEMData or ScopeEMData
			newid = self.ID()
			for dataclass in (data.ScopeEMData,data.CameraEMData):
				tryresult = dataclass(newid)
				try:
					tryresult.update(stuff)
					result = tryresult
					break
				except KeyError:
					result = None

		self.EMnode.statelock.release()
		return result

#		emkey = id[0]
#		stuff = self.node.getEM([emkey])

#<<<<<<< EM.py
#		if emkey == 'scope':
#			result = data.ScopeEMData(self.ID(), initializer=stuff)
#		elif emkey == 'camera':
#			result = data.CameraEMData(self.ID(), initializer=stuff)
#		elif emkey == 'all':
#			result = data.AllEMData(self.ID(), initializer=stuff)
#		else:
#			### could be either CameraEMData or ScopeEMData
#			newid = self.ID()
#			for dataclass in (data.ScopeEMData,data.CameraEMData):
#				tryresult = dataclass(newid)
#				try:
#					tryresult.update(stuff)
#					result = tryresult
#					break
#				except KeyError:
#					result = None
#=======
#	def query(self, id):
#		self.EMnode.statelock.acquire()
#		done_event = threading.Event()
#		self.EMnode.queue.put(Request(done_event, [id[0]]))
#		done_event.wait()
#		#self.EMnode.uiUpdate()
#		result = data.EMData(self.EMnode.ID(), em=self.EMnode.state)
#		self.EMnode.statelock.release()
#>>>>>>> 1.64.2.4
#		return result

	def insert(self, idata):
		if isinstance(idata, data.EMData):
			print idata['id'][:-1], 'attempting to set EM'
#<<<<<<< EM.py
#			self.node.setEM(idata)
#=======
			self.EMnode.statelock.acquire()
			done_event = threading.Event()
			self.EMnode.queue.put(Request(done_event, idata['em']))
			done_event.wait()
			self.EMnode.uiUpdate()
			self.EMnode.statelock.release()
#>>>>>>> 1.64.2.4
			print idata['id'][:-1], 'EM set'
#<<<<<<< EM.py
#=======
#
#	def _insert(self, idata):
#		pass
#
#	# borrowed from NodeDataHandler
#	def setBinding(self, eventclass, func):
#		if issubclass(eventclass, event.Event):
#			datahandler.DataBinder.setBinding(self, eventclass, func)
#>>>>>>> 1.64.2.4
		else:
			node.DataHandler.insert(self, idata)
			

class Request(object):
	def __init__(self, ievent, value):
		self.event = ievent
		self.value = value

class EM(node.Node):
	def __init__(self, id, session, nodelocations,
								scope = None, camera = None, **kwargs):
		# internal
		self.lock = threading.Lock()
		# external
		self.nodelock = threading.Lock()
		self.locknodeid = None

		# should have preferences
		if scope is None:
			scope = ('tecnai', 'tecnai')
		if camera is None:
			camera = ('gatan', 'gatan')

		node.Node.__init__(self, id, session, nodelocations, datahandler=DataHandler, **kwargs)

		self.addEventInput(event.LockEvent, self.doLock)
		self.addEventInput(event.UnlockEvent, self.doUnlock)

		self.queue = Queue.Queue()
		self.state = {}
		self.statelock = threading.RLock()

		self.handlerthread = threading.Thread(name='EM handler thread',
																					target=self.handler,
																					args=(scope, camera))
		self.handlerthread.setDaemon(1)
		self.handlerthread.start()

		self.defineUserInterface()

		self.start()

	def handler(self, scope, camera):
		self.scope = self.camera = {}
		if scope[0]:
			fp, pathname, description = imp.find_module(scope[0])
			scopemodule = imp.load_module(scope[0], fp, pathname, description)
			if scope[1]:
				self.scope = scopedict.factory(scopemodule.__dict__[scope[1]])()
		if camera[0]:
			fp, pathname, description = imp.find_module(camera[0])
			cameramodule = imp.load_module(camera[0], fp, pathname, description)
			if camera[1]:
				self.camera = cameradict.factory(cameramodule.__dict__[camera[1]])()

		self.addEventOutput(event.ListPublishEvent)

		ids = ['scope', 'camera', 'camera no image data', 'all']
		ids += self.scope.keys()
		ids += self.camera.keys()
		for i in range(len(ids)):
			ids[i] = (ids[i],)
		e = event.ListPublishEvent(self.ID(), idlist=ids)
		self.outputEvent(e, wait=True)
		self.outputEvent(event.NodeInitializedEvent(self.ID()))

		self.queueHandler()

	def main(self):
		pass

	def exit(self):
		node.Node.exit(self)
		self.scope.exit()
		self.camera.exit()

	def doLock(self, ievent):
		print 'EM do lock'
		if ievent['id'][:-1] != self.locknodeid:
			self.nodelock.acquire()
			self.locknodeid = ievent['id'][:-1]
			print self.locknodeid, 'acquired EM lock'
		self.confirmEvent(ievent)

	def doUnlock(self, ievent):
		print 'EM do unlock'
		if ievent['id'][:-1] == self.locknodeid:
			print self.locknodeid, 'releasing EM lock'
			self.locknodeid = None
			self.nodelock.release()

	### now this is handled by EMData
	def pruneEMdict(self, emdict):
		'''
		restrict access to certain scope parameters
		'''
		prunekeys = (
			'gun shift',
			'gun tilt',
			'high tension',
			'beam blank',
			'dark field mode',
			'diffraction mode',
			'low dose',
			'low dose mode',
			'screen current',
		)

		for key in prunekeys:
			try:
				del emdict[key]
			except KeyError:
				pass

	def getEM(self, withkeys=None, withoutkeys=None):
		self.lock.acquire()
		result = {}
		if withkeys is not None:
			for EMkey in withkeys:
				if EMkey in self.scope:
					try:
						result[EMkey] = self.scope[EMkey]
					except:	
						print "failed to get '%s'" % EMkey
				elif EMkey in self.camera:
					try:
						result[EMkey] = self.camera[EMkey]
					except:	
						print "failed to get '%s'" % EMkey
				elif EMkey == 'scope':
					result.update(self.scope)
				elif EMkey == 'camera no image data':
					for camerakey in self.camera:
						if camerakey != 'image data':
							result[camerakey] = self.camera[camerakey]
				elif EMkey == 'camera':
					result.update(self.camera)
				elif EMkey == 'all':
					result.update(self.scope)
					result.update(self.camera)
		elif withoutkeys is not None:
			if not ('scope' in withoutkeys or 'all' in withoutkeys):
				for EMkey in self.scope:
					if not EMkey in withoutkeys:
						try:
							result[EMkey] = self.scope[EMkey]
						except:	
							print "failed to get '%s'" % EMkey
			if not ('camera' in withoutkeys or 'all' in withoutkeys):
				for EMkey in self.camera:
					if not EMkey in withoutkeys:
						try:
							result[EMkey] = self.camera[EMkey]
						except:	
							print "failed to get '%s'" % EMkey
		else:
			result.update(self.scope)
			result.update(self.camera)

		self.lock.release()
		self.pruneEMdict(result)
		result['system time'] = time.time()
		return result

	def sortEMdict(self, emdict):
		'''
		sort items in em dict for proper setting order
		'''
		olddict = copy.deepcopy(emdict)
		newdict = strictdict.OrderedDict()

		# I care about these, the rest don't matter
		order = (
			'magnification',
			'spot size',
			'image shift',
			'beam shift',
			'defocus',
			'reset defocus',
			'intensity',
		)
		for key in order:
			try:
				newdict[key] = olddict[key]
				del olddict[key]
			except KeyError:
				pass

		# the rest don't matter
		newdict.update(olddict)
		return newdict

	def setEM(self, emstate):
		self.lock.acquire()

#<<<<<<< EM.py
#		### order the items in EMstate
#		#ordered = self.sortEMdict(EMstate)
#=======
#		# order the items in EMstate
#		ordered = self.sortEMdict(EMstate)
#>>>>>>> 1.64.2.4

		#for EMkey in ordered.keys():
		for emkey, emvalue in emstate.items():
			if emvalue is None:
				continue
			if emkey in self.scope:
				try:
					self.scope[emkey] = emvalue
				except:	
					print "failed to set '%s' to %s" % (emkey, emvalue)
					pass
			elif emkey in self.camera:
				try:
					self.camera[emkey] = emvalue
				except:	
					#print "failed to set '%s' to" % EMkey, EMstate[EMkey]
					pass
		self.lock.release()

	def save(self, filename):
		print "Saving state to file: %s..." % filename,
		try:
			f = file(filename, 'w')
			savestate = self.getEM(withoutkeys=['image data'])
			cPickle.dump(savestate, f)
			f.close()
		except:
			print "Error: failed to save EM state"
			raise
		else:
			print "done."
		return ''

	def load(self, filename):
		print "Loading state from file: %s..." % filename,
		try:
			f = file(filename, 'r')
			loadstate = cPickle.load(f)
			self.setEM(loadstate)
			f.close()
		except:
			print "Error: failed to load EM state"
			raise
		else:
			print "done."
		return ''

	def uiUpdate(self):
		state = copy.copy(self.state)
		try:
			del state['image data']
		except KeyError:
			pass
		uistate = self.statestruct.get()
		uistate.update(state)
		self.statestruct.set(uistate)

	def uiCallback(self, value):
		self.statelock.acquire()
		done_event = threading.Event()
		self.queue.put(Request(done_event, value))
		done_event.wait()
		state = copy.copy(self.state)
		try:
			del state['image data']
		except KeyError:
			pass
		self.statelock.release()
		return state

	def queueHandler(self):
		while True:
			request = self.queue.get()
			if type(request.value) is dict:
				self.setEM(request.value)
				self.state = self.getEM(request.value.keys())
			else:
				self.state = self.getEM(request.value)
			request.event.set()

	def uiUnlock(self):
		self.locknodeid = None
		self.nodelock.release()

	def defineUserInterface(self):
		node.Node.defineUserInterface(self)
		self.statestruct = uidata.UIStruct('Instrument State', {},
																				'rw', self.uiCallback)
		unlockmethod = uidata.UIMethod('Unlock', self.uiUnlock)
		container = uidata.UIMediumContainer('EM')
		container.addUIObjects((self.statestruct, unlockmethod))
		self.uiserver.addUIObject(container)

