#!/usr/bin/python -O

import os
import sys
import time
import wx
import appionLoop
import particleLoop
import apFindEM
import appionData
import apDatabase
import apDisplay
import apParticle
import apPeaks
import ApTiltPicker
import apTiltTransform
import apTiltPair

##################################
##
##################################

class tiltAligner(particleLoop.ParticleLoop):
	#def __init__(self):
	#	raise NotImplementedError()
	
	#####################################################
	##### START PRE-DEFINED PARTICLE LOOP FUNCTIONS #####
	#####################################################

	def setProcessingDirName(self):
		self.processdirname = "tiltalign"

	def preLoopFunctions(self):
		if self.params['dbimages']:
			self.processAndSaveAllImages()
		self.app = ApTiltPicker.PickerApp(0)
		self.app.appionloop = self
		#self.app.quit = wx.Button(self.app.frame, wx.ID_FORWARD, '&Forward')

	def postLoopFunctions(self):
		self.app.frame.Destroy()
		apDisplay.printMsg("Finishing up")
		time.sleep(20)
		apDisplay.printMsg("finished")
		wx.Exit()

	def commitToDatabase(self, imgdata):
		expid = int(imgdata['session'].dbid)
		#self.insertTiltAlignParams(expid)
		return

	def particleDefaultParams(self):
		"""
		put in any additional default parameters
		"""
		self.params['usepicks'] = False
		self.params['outtype'] = 'pickle'
		self.params['outtypeindex'] = None
		self.params['pickrunname'] = None
		self.params['pickrunid'] = None

	def particleParseParams(self, args):
		"""
		put in any additional parameters to parse
		"""
		for arg in args:
			elements = arg.split('=')
			elements[0] = elements[0].lower()
			if arg == 'usepicks':
				self.params['usepicks'] = True
			elif elements[0] == 'outtype':
				self.params['outtype'] = elements[1]
			elif (elements[0]=='pickrunid'):
				self.params['pickrunid']=int(elements[1])
			elif (elements[0]=='pickrunname'):
				self.params['pickrunname']=str(elements[1])
			else:
				apDisplay.printError(str(elements[0])+" is not recognized as a valid parameter")

	def particleParamConflicts(self):
		"""
		put in any additional conflicting parameters
		"""
		for i,v in enumerate(('text','xml','spider','pickle')):
			if self.params['outtype'] == v:
				self.params['outtypeindex'] = i
		if self.params['outtypeindex'] is None:
			apDisplay.printError("outtype must be one of: text, xml, pickle or spider; NOT "+str(self.params['outtype']))
		return

	def particleCreateOutputDirs(self):
		"""
		put in any additional directories to create
		"""
		self.params['pickdatadir'] = os.path.join(self.params['rundir'],"pickdata")
		self._createDirectory(self.params['pickdatadir'], warning=False)
	
		return

	def processImage(self, imgdata):
		# run it
		tiltdata = apTiltPair.getTiltPair(imgdata)
		if tiltdata is not None:
			self.runTiltAligner(imgdata, tiltdata)

		#parse the data
		#self.parseTiltParams()

	def commitToDatabase(self, imgdata):
		"""
		Over-writes the particleLoop commit and uses the appionLoop commit
		"""
		tiltdata = apTiltPair.getTiltPair(imgdata)
		if tiltdata is not None:
			self.expid = int(imgdata['session'].dbid)
			apTiltPair.insertTiltParams(imgdata, tiltdata, self.tiltparams)
			if self.params['usepicks'] is True:
				apParticle.insertParticlePeaks(self.peaktree1, imgdata, self.expid, self.params)
				apParticle.insertParticlePeaks(self.peaktree2, tiltdata, self.expid, self.params)
			if self.assess is not None:
				apDatabase.insertImgAssessmentStatus(imgdata, self.params['runid'], self.assess)

	###################################################
	##### END PRE-DEFINED PARTICLE LOOP FUNCTIONS #####
	###################################################

	def insertTiltAlignParams():
		### query for identical params ###
		tiltparamsq = appionData.ApTiltAlignParamsData()
	 	tiltparamsq['diam'] = self.params['diam']
	 	tiltparamsq['bin'] = self.params['bin']
	 	tiltparamsq['lp_filt'] = self.params['lp']
	 	tiltparamsq['hp_filt'] = self.params['hp']
	 	tiltparamsq['invert'] = self.params['invert']
		tiltparamsq['output_type'] = self.param['outtype']
		if self.params['pickrunid'] is not None:
			manparamsq['oldselectionrun'] = apParticle.getSelectionRunDataFromID(self.params['pickrunid'])
		#tiltparamsdata = appiondb.query(tiltparamsq, results=1)

		### query for identical run name ###
		runq = appionData.ApSelectionRunData()
		runq['name'] = self.params['runid']
		runq['dbemdata|SessionData|session'] = self.expid
		runids = appiondb.query(runq, results=1)

	 	# if no run entry exists, insert new run entry into dbappiondata
	 	if not runids:
			apDisplay.printMsg("Inserting new runId into database")
			runq['tiltparams'] = tiltparamsq
			appiondb.insert(runq)
		return


	def parseTiltParams(self):
		theta = self.tiltparams['theta']
		gamma = self.tiltparams['gamma']
		phi   = self.tiltparams['phi']

	def processAndSaveAllImages(self):
		print "Pre-processing images before picking"
		for imgdata in self.imgtree:
			imgpath = os.path.join(self.params['rundir'], imgdata['filename']+'.dwn.mrc')
			if os.path.isfile(imgpath):
				print "already processed: ",apDisplay.short(imgdata['filename'])
			else:
				apFindEM.processAndSaveImage(imgdata, params=self.params)
			tiltdata = apTiltPair.getTiltPair(imgdata)
			if tiltdata is None:
				continue
			tiltpath = os.path.join(self.params['rundir'], tiltdata['filename']+'.dwn.mrc')
			if os.path.isfile(tiltpath):
				print "already processed: ",apDisplay.short(tiltdata['filename'])
			else:
				apFindEM.processAndSaveImage(tiltdata, params=self.params)

	def insertTiltAlignParams(self, expid):
		tiltparamsq=appionData.ApTiltParamsData()
		tiltparamsq['diam']    = self.params['diam']
		tiltparamsq['lp_filt'] = self.params['lp']
		tiltparamsq['hp_filt'] = self.params['hp']
		tiltparamsq['bin']     = self.params['bin']
		tiltparamsdata = self.appiondb.query(tiltparamsq, results=1)
		
		runq=appionData.ApSelectionRunData()
		runq['name'] = self.params['runid']
		runq['dbemdata|SessionData|session'] = expid
		runids = self.appiondb.query(runq, results=1)
		
		if not runids:
			runq['tiltparams']=tiltparamsq
			self.appiondb.insert(runq)
		else:
			#make sure all params are the same as previous session
			for pkey in tiltparamsq:
				if tiltparamsq[pkey] != tiltparamsdata[0][pkey]:
					print "All parameters for a particular manualpicker run must be identical"
					print pkey,tiltparamsq[pkey],"not equal to",tiltparamsdata[0][pkey]
					sys.exit(1)
			for i in tiltparamsq:
				if tiltparamsdata[0][i] != tiltparamsq[i]:
					apDisplay.printError("All parameters for a particular manualpicker run must be identical\n"+
						str(i)+":"+str(tiltparamsq[i])+" not equal to "+str(tiltparamsdata[0][i]))
		return

	def runTiltAligner(self, imgdata, tiltdata):
		#reset targets
		self.app.onClearPicks(None)
		self.app.onResetParams(None)
		self.tiltparams = {}
		#set tilt
		tilt1 = apDatabase.getTiltAngleDeg(imgdata)
		tilt2 = apDatabase.getTiltAngleDeg(tiltdata)
		self.app.data['theta'] = tilt1 - tilt2
		print "theta=",self.app.data['theta']
		#open new file
		imgname = imgdata['filename']+".dwn.mrc"
		imgpath = os.path.join(self.params['rundir'],imgname)
		self.app.panel1.openImageFile(imgpath)
		#open tilt file
		tiltname = tiltdata['filename']+".dwn.mrc"
		tiltpath = os.path.join(self.params['rundir'],tiltname)
		self.app.panel2.openImageFile(tiltpath)
		#run the picker
		self.app.MainLoop()
		self.app.panel1.openImageFile(None)
		self.app.panel2.openImageFile(None)
		#tilt data are copied to self.tiltparams by app
		#particles picks are copied to self.peaktree1 and self.peaktree2 by app
		self.peaktree1 = apPeaks.convertListToPeaks(self.peaks1, self.params)
		self.peaktree2 = apPeaks.convertListToPeaks(self.peaks2, self.params)

if __name__ == '__main__':
	imgLoop = tiltAligner()
	imgLoop.run()



