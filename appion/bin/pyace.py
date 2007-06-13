#!/usr/bin/python -O

#pythonlib
import os
import sys
import re
import math
import cPickle
import time
#appion
import appionLoop
import apImage
import apDisplay
import apDatabase
import apCtf
import apMatlab
#import apParam
#import apLoop
try:
	import pymat
except:
	apDisplay.matlabError()

class aceLoop(appionLoop.AppionLoop):
	def setProcessingDirName(self):
		self.processdirname = "ace"

	def preLoopFunctions(self):
		apMatlab.checkMatlabPath(self.params)
		acepath = os.path.join(os.getcwd(), self.functionname+".py")
		if not os.path.isfile(acepath):
			apDisplay.printWarning("'"+self.functionname+".py' usually needs to be run in the "+\
				"same directory as all of its matlab files")
		print "Connecting to matlab ... "
		try:
			self.matlab = pymat.open()
			#self.matlab = pymat.open('matlab -nodisplay')
		except:
			apDisplay.matlabError()
		apCtf.mkTempDir(self.params['tempdir'])
		apMatlab.setAceConfig(self.matlab, self.params)

	def postLoopFunctions(self):
		pymat.close(self.matlab)

	def reprocessImage(self, imgdata):
		"""
		Returns 
		True, if an image should be reprocessed
		False, if an image was processed and should NOT be reprocessed
		None, if image has not yet been processed 
		e.g. a confidence less than 80%
		"""
		if self.params['reprocess'] is None:
			return None
		ctfvalue, conf = apCtf.getBestCtfValueForImage(imgdata)
		if ctfvalue is None:
			return None

		if conf > self.params['reprocess']:
			return False
		else:
			return True

	def processImage(self, imgdata):
		# RESTART MATLAB EVERY 500 IMAGES OR IT RUNS OUT OF MEMORY
		if self.stats['count'] % 500 == 0:
			apDisplay.printWarning("processed 500 images. restarting matlab...")
			pymat.close(self.matlab)
			time.sleep(5)
			self.matlab = pymat.open()

		scopeparams = {
			'kv':      imgdata['scope']['high tension']/1000,
			'apix':    apDatabase.getPixelSize(imgdata),
			'cs':      self.params['cs'],
			'tempdir': self.params['tempdir'],
		}
		apMatlab.setScopeParams(self.matlab, scopeparams)
		### RUN ACE
		self.ctfvalue = apMatlab.runAce(self.matlab, imgdata, self.params)


	def commitToDatabase(self, imgdata):
		expid = int(imgdata['session'].dbid)
		apCtf.insertAceParams(self.params, expid)
		apCtf.commitCtfValueToDatabase(imgdata, self.matlab, self.ctfvalue, self.params)

	def specialDefaultParams(self):
		self.params['edgethcarbon']=0.8
		self.params['edgethice']=0.6
		self.params['pfcarbon']=0.9
		self.params['pfice']=0.3
		self.params['overlap']=2
		self.params['fieldsize']=512
		self.params['resamplefr']=1
		self.params['drange']=0
		self.params['tempdir']=None
		self.params['medium']="carbon"
		self.params['cs']=2.0
		self.params['display']=1
		self.params['stig']=0
		self.params['nominal']=None
		self.params['reprocess']=None
		self.params['matdir']=None
		self.params['opimagedir']=None
		self.params['newnominal']=False
		self.params['uncorrected']=False

	def specialCreateOutputDirs(self):
		self.params['matdir']         = os.path.join(self.params['rundir'],"matfiles")
		self.params['opimagedir']     = os.path.join(self.params['rundir'],"opimages")
		self._createDirectory(os.path.join(self.params['matdir']), warning=False)
		self._createDirectory(os.path.join(self.params['opimagedir']), warning=False)
		if self.params['sessionname'] is not None:
			self.params['outtextfile']=os.path.join(self.params['rundir'], self.params['sessionname']+".txt")

	def specialParseParams(self,args):
		for arg in args:
			elements=arg.split('=')
			elements[0] = elements[0].lower()
			#print elements
			if (elements[0]=='help' or elements[0]=='--help' \
				or elements[0]=='-h' or elements[0]=='-help'):
				sys.exit(1)
			elif (elements[0]=='edgethcarbon'):
				self.params['edgethcarbon']=float(elements[1])
			elif (elements[0]=='edgethice'):
				self.params['edgethice']=float(elements[1])
			elif (elements[0]=='pfcarbon'):
				self.params['pfcarbon']=float(elements[1])
			elif (elements[0]=='pfice'):
				self.params['pfice']=float(elements[1])
			elif (elements[0]=='overlap'):
				self.params['overlap']=int(elements[1])
			elif (elements[0]=='fieldsize'):
				self.params['fieldsize']=int(elements[1])
			elif (elements[0]=='resamplefr'):
				self.params['resamplefr']=float(elements[1])
			elif (elements[0]=='drange'):
				drange=int(elements[1])
				if drange == 1 or drange== 0:
					self.params['drange']=drange
				else:
					apDisplay.printError("drange should only be 0 or 1")
			elif (elements[0]=='tempdir'):
				self.params['tempdir']=os.path.abspath(elements[1]+"/")
			elif (elements[0]=='medium'):
				medium=elements[1]
				if medium=='carbon' or medium=='ice':
					self.params['medium']=medium
				else:
					apDisplay.printError("medium can only be 'carbon' or 'ice'")
			elif (elements[0]=='cs'):
				self.params['cs']=float(elements[1])
			elif (elements[0]=='display'):
				display=int(elements[1])
				if display==0 or display==1:
					self.params['display']=display
				else:
					apDisplay.printError("display must be 0 or 1")	
			elif (elements[0]=='stig'):
				stig=int(elements[1])
				if stig==0 or stig==1:
					self.params['stig']=stig
				else:
					apDisplay.printError("stig must be 0 or 1")
			elif (elements[0]=='nominal'):
				self.params['nominal']=float(elements[1])
			elif (elements[0]=='reprocess'):
				self.params['reprocess']=float(elements[1])
			elif (elements[0]=='newnominal'):
				self.params['newnominal']=True
			elif arg == 'uncorrected':
				self.params['uncorrected']=True

	def specialParamConflicts(self):
		if self.params['nominal'] is not None and (self.params['nominal'] > 0 or self.params['nominal'] < -15e-6):
			apDisplay.printError("Nominal should be of the form nominal=-1.2e-6 for -1.2 microns")
		return


if __name__ == '__main__':
	imgLoop = aceLoop()
	imgLoop.run()

