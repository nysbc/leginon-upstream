import copy
import threading
import datahandler

# doens't really lock across processes
# bad things could happen with have multiple sessions and don't specify session

picklefilename = './DataPickle'

class PickleDataKeeper(datahandler.DataHandler):
	def __init__(self, id, session=None):
		datahandler.DataHandler.__init__(self, id)
		self.lock = threading.Lock()
		self.filename = picklefilename
		self.db = {}
		if session is not None:
			self.newSession(session)
		else:
			self._read()
			self.session = self.db['sessions'][-1]

	def newSession(self, session):
		self.lock.acquire()
		self._read()
		self.session = session
		if 'sessions' not in self.db:
			self.db['sessions'] = []
		if 'data' not in self.db:
			self.db['data'] = {}
		if session not in self.db['sessions']:
			self.db['sessions'].append(self.session)
			self.db['data'][self.session] = {}
		self.data = self.db['data'][self.session]
		self._write()
		self.lock.release()

	def query(self, id):
		self.lock.acquire()
		# let exception fall through?
		self._read()
		try:
			# does copy happen elsewhere?
			# taking latest result, need to be able to specify
			result = copy.deepcopy(self.db['data'][self.session][id])
		except KeyError:
			result = None
		self.lock.release()

	# needs to use session id
	def insert(self, newdata):
		self.lock.acquire()
		self._read()
		# does copy happen elsewhere?
		self.db['data'][self.session][newdata.id] = copy.deepcopy(newdata)
		self._write()
		self.lock.release()

	# necessary?
	def remove(self, id):
		self.lock.acquire()
		# all?
		self._read()
		del self.db['data'][self.session][id]
		self._write()
		self.lock.release()

	# necessary?
	def ids(self):
		self.lock.acquire()
		self._read()
		return self.db['data'][self.session].keys()
		self.lock.release()

	def exit(self):
		self.lock.acquire()

	def _read(self):
		#self.lock.acquire()
		try:
			file = open(self.filename, 'rb')
			self.db = cPickle.load(file)
			file.close()
		except:
			self.printerror('cannot read from %s' % self.filename)
		#self.lock.release()

	def _write(self):
		#self.lock.acquire()
		try:
			file = open(self.filename, 'wb')
			cPickle.dump(self.db, file, bin=True)
			file.close()
		except IOError:
			self.printerror('cannot write to %s' % self.filename)
		#self.lock.release()

