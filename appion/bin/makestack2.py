#!/usr/bin/env python

#pythonlib
import os
import sys
import math
import re
import time
import glob
import socket
import numpy
import subprocess
#appion
import appionLoop2
import apImage
import apDisplay
import apDatabase
import apCtf
import apStack
import apDefocalPairs
import appionData
import apParticle
import apStackMeanPlot
import apEMAN
import apProject
import apFile
import apParam
import apImagicFile


class Makestack2Loop(appionLoop2.AppionLoop):

	############################################################
	## Check pixel size
	############################################################
	def checkPixelSize(self):
		# make sure that images all have same pixel size:
		# first get pixel size of first image:
		if len(self.imgtree) == 0:
			return
		self.params['apix'] = apDatabase.getPixelSize(self.imgtree[0])
		for imgdata in self.imgtree:
			# get pixel size
			if apDatabase.getPixelSize(imgdata) != self.params['apix']:
				apDisplay.printWarning("This particle selection run contains images of varying pixelsizes, a stack cannot be created")

	############################################################
	## Retrive existing stack info
	############################################################
	def getExistingStackInfo(self):
		stackfile=os.path.join(self.params['rundir'], self.params['single'])
		stackid = apStack.getStackIdFromPath(stackfile)
		numdbpart = len(apStack.getStackParticlesFromId(stackid))

		if numdbpart == 0:
			self.params['continue'] = False
			apDisplay.printWarning("file exists but no particles in database, deleting stack file")
			apFile.removeStack(stackfile)
			return 0

		### we now have particles in the database
		if self.params['continue'] is False:
			apDisplay.printWarning("particles exist in database, must force continue")
			self.params['continue'] = True

		### we better have the same number of particles in the file and the database
		numfilepart = apFile.numImagesInStack(stackfile)
		if numfilepart != numdbpart:
			apDisplay.printError("database and file have different number of particles, create a new stack this one is corrupt")

		return numfilepart


	############################################################
	##  skip image if additional criteria is not met
	############################################################
	def rejectImage(self, imgdata):
		shortname = apDisplay.short(imgdata['filename'])

		if self.params['mag']:
			if not apDatabase.checkMag(imgdata, self.params['mag']):
				apDisplay.printColor(shortname+" was not at the specific magnification","cyan")
				return False

		return True

	############################################################
	## get CTF parameters and skip image if criteria is not met
	############################################################
	def checkCtfParams(self, imgdata):
		shortname = apDisplay.short(imgdata['filename'])
		ctfvalue, conf = apCtf.getBestCtfValueForImage(imgdata)

		### check if we have values and if we care
		if ctfvalue is None:
			if self.params['acecutoff'] or self.params['mindefocus'] or self.params['maxdefocus'] or self.params['phaseflipped']:
				#apDisplay.printColor(shortname+" was rejected because it has no ACE values\n","cyan")
				return False
			else:
				#apDisplay.printWarning(shortname+" has no ACE values")
				return True

		### check that ACE estimation is above confidence threshold
		if self.params['acecutoff'] and conf < self.params['acecutoff']:
			#apDisplay.printColor(shortname+" is below ACE threshold (conf="+str(round(conf,3))+")\n","cyan")
			return False

		### get best defocus value
		### defocus should be in negative meters
		if ctfvalue['defocus2'] is not None and ctfvalue['defocus1'] != ctfvalue['defocus2']:
			defocus = (ctfvalue['defocus1'] + ctfvalue['defocus2'])/2.0
		else:
			defocus = ctfvalue['defocus1']
		defocus = -1.0*abs(defocus)

		### skip micrograph that have defocus above or below min & max defocus levels
		if self.params['mindefocus'] and defocus > self.params['mindefocus']:
			#apDisplay.printColor(shortname+" defocus ("+str(round(defocus*1e6,2))+\
			#	" um) is less than mindefocus ("+str(self.params['mindefocus']*1e6)+" um)\n","cyan")
			return False
		if self.params['maxdefocus'] and defocus < self.params['maxdefocus']:
			#apDisplay.printColor(shortname+" defocus ("+str(round(defocus*1e6,2))+\
			#	" um) is greater than maxdefocus ("+str(self.params['maxdefocus']*1e6)+" um)\n","cyan")
			return False

		return True

	#=======================
	def boxParticlesFromImage(self, imgdata):
		shortname = apDisplay.short(imgdata['filename'])
		imgpath = os.path.join(imgdata['session']['image path'], imgdata['filename']+".mrc")

		### get the particle before image filtering
		if self.params['defocpair'] is True:
			partdatas, shiftdata = apParticle.getDefocPairParticles2(imgdata, self.params['selectionid'])
		else:
			partdatas = apParticle.getParticles(imgdata, self.params['selectionid'])
			shiftdata = {'shiftx':0, 'shifty':0, 'scale':1}

		### apply correlation limits
		if self.params['correlationmin'] or self.params['correlationmax']:
			partdatas = self.eliminateMinMaxCCParticles(partdatas)

		### apply masks
		if self.params['checkmask']:
			partdatas = self.eliminateMaskedParticles(partdatas, imgdata)

		### check if we have particles
		if len(partdatas) == 0:
			apDisplay.printColor(shortname+" has no remaining particles and has been rejected\n","cyan")
			return None, None, None

		### save particle coordinates to box file
		boxedpartdatas, emanboxfile = self.writeParticlesToBoxFile(partdatas, shiftdata, imgdata)

		if self.params['boxfiles']:
			return None, None, None

		### check if we have particles again
		if len(boxedpartdatas) == 0:
			apDisplay.printColor(shortname+" has no remaining particles and has been rejected\n","cyan")
			return None, None, None

		if self.params['uncorrected']:
			### dark/bright correct image
			tmpname = shortname+"-darknorm.dwn.mrc"
			imgarray = apImage.correctImage(imgdata, self.params['sessionname'])
			imgpath = os.path.join(self.params['rundir'], tmpname)
			apImage.arrayToMrc(imgarray,imgpath)
			print "processing", imgpath

		t0 = time.time()
		if self.params['phaseflipped'] is True:
			if self.params['fliptype'] == 'emanimage':
				### ctf correct whole image using EMAN
				imgpath = self.phaseFlipWholeImage(imgpath, imgdata)
				self.ctftimes.append(time.time()-t0)
			elif self.params['fliptype'] == "ace2image":
				### ctf correct whole image using Ace 2
				imgpath = self.phaseFlipAceTwo(imgpath, imgdata)
				self.ctftimes.append(time.time()-t0)
		if imgpath is None:
			return None, None, None
		
		### run batchboxer command
		imgstackfile = os.path.join(self.params['rundir'], shortname+".hed")
		emancmd = "batchboxer input=%s dbbox=%s output=%s newsize=%i" %(imgpath, emanboxfile, imgstackfile, self.params['boxsize'])
		apDisplay.printMsg("boxing "+str(len(boxedpartdatas))+" particles into temp file: "+imgstackfile)
		t0 = time.time()
		apEMAN.executeEmanCmd(emancmd, showcmd=True, verbose=True)
		self.batchboxertimes.append(time.time()-t0)

		### read mean and stdev
		partmeantree = []
		t0 = time.time()
		imagicdata = apImagicFile.readImagic(imgstackfile)
		### loop over the particles and read data
		for i in range(len(boxedpartdatas)):
			partdata = boxedpartdatas[i]
			partarray = imagicdata['images'][i]
			# take abs of mean, because ctf whole image may become negative
			partmeandict = {
				'partdata': partdata,
				'mean': abs(partarray.mean()),
				'stdev': partarray.std(),
				'min': partarray.min(),
				'max': partarray.max(),
			}
			if partmeandict['mean'] > 1.0e7:
				partmeandict['mean'] /= 1.0e7
			if partmeandict['stdev'] > 1.0e7:
				partmeandict['stdev'] /= 1.0e7
			partmeantree.append(partmeandict)
		self.meanreadtimes.append(time.time()-t0)

		### phase flipping
		t0 = time.time()
		if self.params['phaseflipped'] is True:
			if self.params['fliptype'] == 'emantilt':
				### ctf correct individual particles with tilt using Eman
				imgstackfile = self.tiltPhaseFlipParticles(imgdata, imgstackfile, boxedpartdatas)
				self.ctftimes.append(time.time()-t0)
			elif self.params['fliptype'] == 'emanpart':
				### ctf correct individual particles using Eman
				imgstackfile = self.phaseFlipParticles(imgdata, imgstackfile)
				self.ctftimes.append(time.time()-t0)
			else:
				apDisplay.printMsg("phase flipped whole image already")
		else:
			apDisplay.printMsg("not phase flipping particles")

		numpart = apFile.numImagesInStack(imgstackfile)
		apDisplay.printMsg(str(numpart)+" particles were boxed out from "+shortname)

		if len(boxedpartdatas) != numpart:
			apDisplay.printError("There is a mismatch in the number of particles expected and that were boxed")

		return boxedpartdatas, imgstackfile, partmeantree

	#=======================
	def writeParticlesToBoxFile(self, partdatas, shiftdata, imgdata):
		imgdims = imgdata['camera']['dimension']
		fullbox = self.params['boxsize']
		halfbox = self.params['boxsize']/2
		emanboxfile = os.path.join(self.params['rundir'], apDisplay.short(imgdata['filename'])+"-eman.box")

		boxedpartdatas = []
		eliminated = 0
		boxfile=open(emanboxfile, 'w')
		for i in range(len(partdatas)):
			partdata = partdatas[i]
			xcoord= int(round( shiftdata['scale']*(partdata['xcoord'] - shiftdata['shiftx']) - halfbox ))
			ycoord= int(round( shiftdata['scale']*(partdata['ycoord'] - shiftdata['shifty']) - halfbox ))

			if ( (xcoord > 0 and xcoord+fullbox <= imgdims['x']) 
			and  (ycoord > 0 and ycoord+fullbox <= imgdims['y']) ):
				boxfile.write("%d\t%d\t%d\t%d\t-3\n"%(xcoord,ycoord,fullbox,fullbox))
				boxedpartdatas.append(partdata)
			else:
				eliminated += 1

		if eliminated > 0:
			apDisplay.printMsg(str(eliminated)+" particle(s) eliminated because they were out of bounds")
		boxfile.close()
		return boxedpartdatas, emanboxfile

	############################################################
	############################################################
	## CTF correction functions
	############################################################
	############################################################

	#=======================
	def tiltPhaseFlipParticles(self, imgdata, imgstackfile, partdatas):
		ctfvalue = apCtf.getBestTiltCtfValueForImage(imgdata)
		if ctfvalue is None:
			apDisplay.printError("Failed to get ctf parameters")
		apix = apDatabase.getPixelSize(imgdata)
		ctfimgstackfile = os.path.join(self.params['rundir'], apDisplay.short(imgdata['filename'])+"-ctf.hed")

		### calculate defocus at given position
		CX = imgdata['camera']['dimension']['x']
		CY = imgdata['camera']['dimension']['y']

		if ctfvalue['tilt_axis_angle'] is not None:
			N1 = -1.0 * math.sin( math.radians(ctfvalue['tilt_axis_angle']) )
			N2 = math.cos( math.radians(ctfvalue['tilt_axis_angle']) )
		else:
			N1 = 0.0
			N2 = 1.0
		PSIZE = apix

		### High tension on CM is given in kv instead of v so do not divide by 1000 in that case
		if imgdata['scope']['tem']['name'] == "CM":
			voltage = imgdata['scope']['high tension']
		else:
			voltage = (imgdata['scope']['high tension'])/1000

		imagicdata = apImagicFile.readImagic(imgstackfile)
		ctfpartstack = []
		for i in range(len(partdatas)):
			partdata = partdatas[i]
			prepartarray = imagicdata['images'][i]
			prepartmrc = "rawpart.dwn.mrc"
			postpartmrc = "ctfpart.dwn.mrc"
			apImage.arrayToMrc(partarray, prepartmrc, msg=False)

			### calculate ctf based on position
			DX = CX - partdata['xcoord']
			DY = CY - partdata['ycoord']
			DF = (N1*DX + N2*DY) * PSIZE * math.tan( math.radians(ctfvalue['tilt_angle']) )
			DFL1 = ctfvalue['defocus1']*-1.0e4 + DF
			DFL2 = ctfvalue['defocus2']*-1.0e4 + DF
			DF_final = (DFL1+DFL2)/2.0

			### convert defocus to meters
			defocus = DF_final*-1.0e-4

			self.checkDefocus(defocus, shortname)

			parmstr = ("parm=%f,200,1,%.3f,0,17.4,9,1.53,%i,2,%f" %(defocus, ampconst, voltage, apix))
			emancmd = ("applyctf %s %s %s setparm flipphase" % (prepartmrc, postpartmrc, parmstr))
			apEMAN.executeEmanCmd(emancmd, showcmd=True)

			ctfpartarray = apImage.mrcToArray(postpartmrc)
			ctfpartstack.append(ctfpartarray)

		apImagicFile.writeImagic(ctfpartstack, ctfimgstackfile)

	#=======================
	def phaseFlipParticles(self, imgdata, imgstackfile):
		imgname = imgdata['filename']
		shortname = apDisplay.short(imgname)
		ctfimgstackfile = os.path.join(self.params['rundir'], apDisplay.short(imgdata['filename'])+"-ctf.hed")

		### High tension on CM is given in kv instead of v so do not divide by 1000 in that case
		if imgdata['scope']['tem']['name'] == "CM":
			voltage = imgdata['scope']['high tension']
		else:
			voltage = (imgdata['scope']['high tension'])/1000

		apix = apDatabase.getPixelSize(imgdata)
		defocus, ampconst = apCtf.getBestDefocusAndAmpConstForImage(imgdata, msg=True)
		defocus *= 1.0e6
		self.checkDefocus(defocus, shortname)

		parmstr = ("parm=%f,200,1,%.3f,0,17.4,9,1.53,%i,2,%f" %(defocus, ampconst, voltage, apix))
		emancmd = ("applyctf %s %s %s setparm flipphase" % (imgstackfile, ctfimgstackfile, parmstr))

		apDisplay.printMsg("phaseflipping particles with defocus "+str(round(defocus,3))+" microns")
		apEMAN.executeEmanCmd(emancmd, showcmd=True)
		return ctfimgstackfile

	#=======================
	def phaseFlipWholeImage(self, inimgpath, imgdata):
		imgname = imgdata['filename']
		shortname = apDisplay.short(imgname)
		outimgpath = os.path.join(self.params['rundir'], shortname+"-ctfcorrect.dwn.mrc")

		### High tension on CM is given in kv instead of v so do not divide by 1000 in that case
		if imgdata['scope']['tem']['name'] == "CM":
			voltage = imgdata['scope']['high tension']
		else:
			voltage = (imgdata['scope']['high tension'])/1000

		apix = apDatabase.getPixelSize(imgdata)
		defocus, ampconst = apCtf.getBestDefocusAndAmpConstForImage(imgdata, msg=True)
		defocus *= 1.0e6
		self.checkDefocus(defocus, shortname)

		parmstr = ("parm=%f,200,1,%.3f,0,17.4,9,1.53,%i,2,%f" %(defocus, ampconst, voltage, apix))
		emancmd = ("applyctf %s %s %s setparm flipphase" % (inimgpath, outimgpath, parmstr))

		apDisplay.printMsg("phaseflipping entire micrograph with defocus "+str(round(defocus,3))+" microns")
		apEMAN.executeEmanCmd(emancmd, showcmd=True)
		return outimgpath

	#======================
	def getACE2Path(self):
		exename = 'ace2correct.exe'
		ace2exe = subprocess.Popen("which "+exename, shell=True, stdout=subprocess.PIPE).stdout.read().strip()
		if not os.path.isfile(ace2exe):
			ace2exe = os.path.join(apParam.getAppionDirectory(), 'bin', exename)
		if not os.path.isfile(ace2exe):
			apDisplay.printError(exename+" was not found at: "+apParam.getAppionDirectory())
		return ace2exe

	#=======================
	def phaseFlipAceTwo(self, inimgpath, imgdata):

		apix = apDatabase.getPixelSize(imgdata)
		bestctfvalue, bestconf = apCtf.getBestAceTwoValueForImage(imgdata, msg=True)

		if bestctfvalue is None:
			apDisplay.printWarning("No ACE2 ctf estimation for current image")
			self.badprocess = True
			return None
			
		if bestctfvalue['acerun'] is None:
			apDisplay.printWarning("No ACE2 runid for current image")
			self.badprocess = True
			return None
		
		if bestctfvalue['ctfvalues_file'] is None:
			apDisplay.printWarning("No ACE2 ctf file for current image")
			self.badprocess = True
			return None
		
		defocus1 = bestctfvalue['defocus1']
		defocus2 = bestctfvalue['defocus2']
		ampconst = bestctfvalue['amplitude_contrast']
		defocus = (defocus1+defocus2)/2.0*1.0e6
		
		ctfvaluesfile = os.path.join(bestctfvalue['acerun']['path']['path'], bestctfvalue['ctfvalues_file'])
		
		ctfvaluesfilesplit = os.path.splitext(ctfvaluesfile)
		while ctfvaluesfilesplit[1] != '.mrc':
			ctfvaluesfilesplit = os.path.splitext(ctfvaluesfilesplit[0])
		
		ctfvaluesfile = ctfvaluesfilesplit[0]+".mrc.ctf.txt"
		
		apDisplay.printMsg("using ctfvaluesfile: "+ctfvaluesfile)
		
		if not os.path.isfile(ctfvaluesfile):
			apDisplay.printError("ctfvaluesfile does not exist")

		ace2exe = self.getACE2Path()
		ace2cmd = (ace2exe+" -ctf %s -apix %.3f -img %s -wiener 0.1" % (ctfvaluesfile, apix, inimgpath))
		apDisplay.printMsg("ace2 command: "+ace2cmd)
		apDisplay.printMsg("phaseflipping entire micrograph with defocus "+str(round(defocus,3))+" microns")

		### hate to do this but have to, MATLAB's bad fftw3 library gets linked otherwise
		hostname = socket.gethostname()
		try:
			user = os.getlogin()
		except:
			user = None
		if hostname[:5] == "guppy" or (user != "craigyk" and user != "vossman"):
			ace2cmd = "unset LD_LIBRARY_PATH; "+ace2cmd

		#apEMAN.executeEmanCmd(ace2cmd, showcmd=True)
		if self.params['verbose'] is True:
			ace2proc = subprocess.Popen(ace2cmd, shell=True)
		else:
			aceoutf = open("ace2.out", "a")
			aceerrf = open("ace2.err", "a")
			ace2proc = subprocess.Popen(ace2cmd, shell=True, stderr=aceerrf, stdout=aceoutf)	
		ace2proc.wait()
		if self.stats['count'] <= 1:
			### ace2 always crashes on first image??? .fft_wisdom file??
			time.sleep(1)
			if self.params['verbose'] is True:
				ace2proc = subprocess.Popen(ace2cmd, shell=True)
			else:
				aceoutf = open("ace2.out", "a")
				aceerrf = open("ace2.err", "a")
				ace2proc = subprocess.Popen(ace2cmd, shell=True, stderr=aceerrf, stdout=aceoutf)	
			ace2proc.wait()
		
		if self.params['verbose'] is False:	
			aceoutf.close()
			aceerrf.close()

		outfile = os.path.join(os.getcwd(),imgdata['filename']+".mrc.corrected.mrc")

		if not os.path.isfile(outfile):
			apDisplay.printError("ACE 2 failed to create image file")

		return outfile


############################################################
## General functions
############################################################

	#=======================
	def checkDefocus(self, defocus, shortname):
		if defocus > 0:
			apDisplay.printError("defocus is positive "+str(defocus)+" for image "+shortname)
		elif defocus < -1.0e3:
			apDisplay.printError("defocus is very big "+str(defocus)+" for image "+shortname)
		elif defocus > -1.0e-3:
			apDisplay.printError("defocus is very small "+str(defocus)+" for image "+shortname)

	#=======================
	def eliminateMinMaxCCParticles(self, particles):
		newparticles = []
		eliminated = 0
		for prtl in particles:
			if self.params['correlationmin'] and prtl['correlation'] < self.params['correlationmin']:
				eliminated += 1
			elif self.params['correlationmax'] and prtl['correlation'] > self.params['correlationmax']:
				eliminated += 1
			else:
				newparticles.append(prtl)
		if eliminated > 0:
			apDisplay.printMsg(str(eliminated)+" particle(s) eliminated due to min or max correlation cutoff")
		return newparticles

	#=======================
	def eliminateMaskedParticles(self, particles, imgdata):
		newparticles = []
		eliminated = 0
		sessiondata = apDatabase.getSessionDataFromSessionName(self.params['sessionname'])
		if self.params['defocpair']:
			imgdata = apDefocalPairs.getTransformedDefocPair(imgdata,2)
		maskimg,maskbin = apMask.makeInspectedMask(sessiondata,self.params['checkmask'],imgdata)
		if maskimg is not None:
			for prtl in particles:
				binnedcoord = (int(prtl['ycoord']/maskbin),int(prtl['xcoord']/maskbin))
				if maskimg[binnedcoord] != 0:
					eliminated += 1
				else:
					newparticles.append(prtl)
			print eliminated,"particle(s) eliminated due to masking"
		else:
			print "no masking"
			newparticles = particles
		return newparticles

	#=======================
	def mergeImageStackIntoBigStack(self, imgstackfile, imgdata):
		bigimgstack = os.path.join(self.params['rundir'], self.params['single'])

		emancmd="proc2d %s %s" %(imgstackfile, bigimgstack)
		### normalization
		if self.params['normalized'] is True:
			emancmd += " norm=0.0,1.0"
			# edge normalization
			emancmd += " edgenorm"
		### high / low pass filtering
		if self.params['highpass'] or self.params['lowpass']:
			emancmd += " apix=%s" % apDatabase.getPixelSize(imgdata)
			if self.params['highpass']:
				emancmd += " hp=%.2f" % self.params['highpass']
			if self.params['lowpass']:
				emancmd += " lp=%.2f" % self.params['lowpass']
		### bin images if specified
		if self.params['bin'] > 1:
			emancmd += " shrink=%d"%(self.params['bin'])
		emancmd += " clip=%d,%d"%(self.params['boxsize'],self.params['boxsize'])
		### unless specified, invert the images
		if self.params['inverted'] is True:
			emancmd += " invert"
		### if specified, create spider stack
		if self.params['spider'] is True:
			emancmd += " spiderswap"

		apDisplay.printMsg("appending particles to stack: "+bigimgstack)
		t0 = time.time()
		apEMAN.executeEmanCmd(emancmd)
		self.mergestacktimes.append(time.time()-t0)

		### count particles
		bigcount = apFile.numImagesInStack(bigimgstack, self.params['boxsize']/self.params['bin'])
		imgcount = apFile.numImagesInStack(imgstackfile, self.params['boxsize'])

		### append to particle log file
		partlogfile = os.path.join(self.params['rundir'], self.timestamp+"-particles.info")
		f = open(partlogfile, 'a')
		for i in range(imgcount):
			partnum = self.particleNumber + i + 1
			line = str(partnum)+'\t'+os.path.join(imgdata['session']['image path'], imgdata['filename']+".mrc")
			f.write(line+"\n")
		f.close()

		return bigcount

############################################################
## Insert and Committing
############################################################

	#=======================
	def insertStackRun(self):
		sessiondata = apDatabase.getSessionDataFromSessionName(self.params['sessionname'])
		projectnum = apProject.getProjectIdFromSessionName(self.params['sessionname'])

		stparamq=appionData.ApStackParamsData()
		paramlist = ('boxSize','bin','aceCutoff','correlationMin','correlationMax',
			'checkMask','minDefocus','maxDefocus','fileType','inverted','normalized', 'defocpair',
			'lowpass','highpass','norejects', 'tiltangle')

		### fill stack parameters
		for p in paramlist:
			if p.lower() in self.params:
				stparamq[p] = self.params[p.lower()]
			else:
				print "missing", p.lower()
		if self.params['phaseflipped'] is True:
			stparamq['phaseFlipped'] = True
			stparamq['fliptype'] = self.params['fliptype']
		paramslist = stparamq.query()

		if not 'boxSize' in stparamq or stparamq['boxSize'] is None:
			print stparamq
			apDisplay.printError("problem in database insert")

		### create a stack object
		stackq = appionData.ApStackData()
		stackq['path'] = appionData.ApPathData(path=os.path.abspath(self.params['rundir']))
      	### see if stack already exists in the database (just checking path & name)
		uniqstackdatas = stackq.query(results=1)

		### create a stackRun object
		runq = appionData.ApStackRunData()
		runq['stackRunName'] = self.params['runname']
		runq['session'] = sessiondata
      	### see if stack run already exists in the database (just checking runname & session)
		uniqrundatas = runq.query(results=1)

      	### finish stack object
		stackq['name'] = self.params['single']
		stackq['description'] = self.params['description']
		stackq['hidden'] = False
		stackq['pixelsize'] = self.params['apix']*self.params['bin']*1e-10
		stackq['project|projects|project'] = projectnum
		self.stackdata = stackq

      	### finish stackRun object
		runq['stackParams'] = stparamq
		self.stackrundata = runq

      	### create runinstack object
		rinstackq = appionData.ApRunsInStackData()
		rinstackq['stackRun'] = runq
#		rinstackq['stack'] = stackq
		rinstackq['project|projects|project'] = projectnum

      	### if not in the database, make sure run doesn't already exist
		if not uniqstackdatas and not uniqrundatas:
			apDisplay.printColor("Inserting stack parameters into database", "cyan")
			if self.params['commit'] is True:
				rinstackq['stack'] = stackq
				rinstackq.insert()
			return
		elif uniqrundatas and not uniqstackdatas:
			apDisplay.printError("Weird, run data without stack already in the database")
		else:

			rinstack = rinstackq.query(results=1)

			prevrinstackq = appionData.ApRunsInStackData()
			prevrinstackq['stackRun'] = uniqrundatas[0]
			prevrinstackq['stack'] = uniqstackdatas[0]
			prevrinstackq['project|projects|project'] = projectnum
			prevrinstack = prevrinstackq.query(results=1)

			## if no runinstack found, find out which parameters are wrong:
			if not rinstack:
				for i in uniqrundatas[0]:
					print "r =======",i,"========"
					if uniqrundatas[0][i] != runq[i]:
						apDisplay.printError("the value for parameter '"+str(i)+"' is different from before")
					else:
						print i,uniqrundatas[0][i],runq[i]
				for i in uniqrundatas[0]['stackParams']:
					print "p =======",i,"========"
					if uniqrundatas[0]['stackParams'][i] != stparamq[i]:
						apDisplay.printError("the value for parameter '"+str(i)+"' is different from before")
					else:
						print i, uniqrundatas[0]['stackParams'][i], stparamq[i]
				for i in uniqstackdatas[0]:
					print "s =======",i,"========"
					if uniqstackdatas[0][i] != stackq[i]:
						apDisplay.printError("the value for parameter '"+str(i)+"' is different from before")
					else:
						print i,uniqstackdatas[0][i],stackq[i]
				for i in prevrinstack[0]:
					print "rin =======",i,"========"
					if prevrinstack[0][i] != rinstackq[i]:
						print i,prevrinstack[0][i],rinstackq[i]
						apDisplay.printError("the value for parameter '"+str(i)+"' is different from before")
					else:
						print i,prevrinstack[0][i],rinstackq[i]
				apDisplay.printError("All parameters for a particular stack must be identical! \n"+\
							     "please check your parameter settings.")
			apDisplay.printWarning("Stack already exists in database! Will try and appending new particles to stack")
		return

	############################################################
	## Common parameters
	############################################################

	#=======================
	def setupParserOptions(self):
		self.flipoptions = ('emanimage', 'emanpart', 'emantilt', 'ace2image')

		### values
		self.parser.add_option("--bin", dest="bin", type="int", default=1,
			help="Bin the particles after boxing", metavar="#")
		self.parser.add_option("--single", dest="single", default="start.hed",
			help="create a single stack")
		self.parser.add_option("--acecutoff", dest="acecutoff", type="float",
			help="ACE cut off")
		self.parser.add_option("--boxsize", dest="boxsize", type="int",
			help="particle box size in pixel")
		self.parser.add_option("--mincc", dest="correlationmin", type="float",
			help="particle correlation mininum")
		self.parser.add_option("--maxcc", dest="correlationmax", type="float",
			help="particle correlation maximum")
		self.parser.add_option("--mindef", dest="mindefocus", type="float",
			help="minimum defocus")
		self.parser.add_option("--maxdef", dest="maxdefocus", type="float",
			help="maximum defocus")
		self.parser.add_option("--selectionid", dest="selectionid", type="int",
			help="particle picking runid")
		self.parser.add_option("--partlimit", dest="partlimit", type="int",
			help="particle limit")
		self.parser.add_option("--filetype", dest="filetype", default='imagic',
			help="filetype, default=imagic")
		self.parser.add_option("--lp", "--lowpass", dest="lowpass", type="float",
			help="low pass filter")
		self.parser.add_option("--hp", "--highpass", dest="highpass", type="float",
			help="high pass filter")
		self.parser.add_option("--mag", dest="mag", type="int",
			help="process only images of magification, mag")

		### true/false
		self.parser.add_option("--phaseflip", dest="phaseflipped", default=False,
			action="store_true", help="perform CTF correction on the boxed images")
		self.parser.add_option("--invert", dest="inverted", default=False,
			action="store_true", help="tilt angle of the micrographs")
		self.parser.add_option("--no-invert", dest="inverted", default=False,
			action="store_false", help="tilt angle of the micrographs")
		self.parser.add_option("--spider", dest="spider", default=False,
			action="store_true", help="create a spider stack")
		self.parser.add_option("--normalized", dest="normalized", default=False,
			action="store_true", help="normalize the entire stack")
		self.parser.add_option("--defocpair", dest="defocpair", default=False,
			action="store_true", help="select defocal pair")

		self.parser.add_option("--no-meanplot", dest="meanplot", default=True,
			action="store_false", help="do not make stack mean plot")

		self.parser.add_option("--boxfiles", dest="boxfiles", default=False,
			action="store_true", help="create only boxfiles, no stack")
		self.parser.add_option("--checkmask", dest="checkmask", default=False,
			action="store_true", help="Check masks")
		self.parser.add_option("--keepall", dest="keepall", default=False,
			action="store_true", help="Do not delete CTF corrected MRC files when finishing")
		self.parser.add_option("--verbose", dest="verbose", default=False,
			action="store_true", help="Show extra ace2 information while running")

		### option based
		#self.parser.add_option("--whole-image", dest="wholeimage", default=False,
		#	action="store_true", help="whole image ctf correction with EMAN")
		#self.parser.add_option("--acetwo", dest="acetwo", default=False,
		#	action="store_true", help="whole image ctf correction with Ace 2")
		#self.parser.add_option("--tiltedflip", dest="tiltedflip", default=False,
		#	action="store_true", help="using tilted defocus estimation based on particle location")
		self.parser.add_option("--flip-type", dest="fliptype",
			help="CTF correction method", metavar="TYPE", 
			type="choice", choices=self.flipoptions, default="emanpart" )

	#=======================
	def checkConflicts(self):
		if self.params['boxsize'] is None:
			apDisplay.printError("A boxsize has to be specified")
		goodboxes = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 
			24, 25, 27, 28, 30, 32, 35, 36, 40, 42, 45, 48, 49, 50, 54, 56, 60, 
			63, 64, 70, 72, 75, 80, 81, 84, 90, 96, 98, 100, 105, 108, 112, 120, 
			125, 126, 128, 135, 140, 144, 147, 150, 160, 162, 168, 175, 180, 189, 
			192, 196, 200, 210, 216, 224, 225, 240, 243, 245, 250, 252, 256, 270, 
			280, 288, 294, 300, 315, 320, 324, 336, 343, 350, 360, 375, 378, 384, 392, 400]
		if not self.params['boxsize'] in goodboxes and self.params['boxsize'] <= 400:
			apDisplay.printWarning("Boxsize does not contain recommended prime numbers")
			for box in goodboxes:
				if box > self.params['boxsize']:
					bigbox = box
					break
				smallbox = box
			apDisplay.printWarning("You should use %d or %d for a boxsize instead"%(smallbox,bigbox))
		if self.params['description'] is None:
			apDisplay.printError("A description has to be specified")
		if (self.params['mindefocus'] is not None and
				(self.params['mindefocus'] < -1e-3 or self.params['mindefocus'] > -1e-9)):
			apDisplay.printError("min defocus is not in an acceptable range, e.g. mindefocus=-1.5e-6")
		if (self.params['maxdefocus'] is not None and
				(self.params['maxdefocus'] < -1e-3 or self.params['maxdefocus'] > -1e-9)):
			apDisplay.printError("max defocus is not in an acceptable range, e.g. maxdefocus=-1.5e-6")
		if self.params['selectionid'] is None and self.params['sessionname'] is not None:
			self.params['selectionid'] = apParticle.guessParticlesForSession(sessionname=self.params['sessionname'])
		if self.params['selectionid'] is None:
			apDisplay.printError("no selection id was provided")


	#=====================
	def setRunDir(self):
		if self.params['sessionname'] is None:
			apDisplay.printError("Please provide a sessionname or run directory")
		#auto set the output directory
		sessiondata = apDatabase.getSessionDataFromSessionName(self.params['sessionname'])
		path = os.path.abspath(sessiondata['image path'])
		path = re.sub("leginon","appion",path)
		path = re.sub("/rawdata","",path)
		path = os.path.join(path, self.processdirname, self.params['runname'])
		self.params['rundir'] = path

	#=======================
	def preLoopFunctions(self):
		self.batchboxertimes = []
		self.ctftimes = []
		self.mergestacktimes = []
		self.meanreadtimes = []
		self.insertdbtimes = []
		self.checkPixelSize()
		if self.params['commit'] is True:
			self.insertStackRun()
			self.particleNumber = self.getExistingStackInfo()
		else:
			self.particleNumber = 0
			stackfile=os.path.join(self.params['rundir'], self.params['single'])
			apFile.removeStack(stackfile)

		apDisplay.printMsg("Starting at particle number: "+str(self.particleNumber))

		if self.params['partlimit'] is not None and self.particleNumber > self.params['partlimit']:
			apDisplay.printError("Number of particles in existing stack already exceeds limit!")

	#=====================
	def reprocessImage(self, imgdata):
		"""
		Returns
		True, if an image should be reprocessed
		False, if an image was processed and should NOT be reprocessed
		None, if image has not yet been processed
		e.g. a confidence less than 80%
		"""
		# check to see if image is rejected by other criteria
		if self.rejectImage(imgdata) is False:
			return False
		# check CTF parameters for image and skip if criteria is not met
		if self.checkCtfParams(imgdata) is False:
			return False
		return None

	#=======================
	def processImage(self, imgdata):
		imgname = imgdata['filename']
		shortname = apDisplay.short(imgdata['filename'])

		### first remove any existing boxed files
		shortfileroot = os.path.join(self.params['rundir'], shortname)
		rmfiles = glob.glob(shortfileroot+"*")
		for rmfile in rmfiles:
			apFile.removeFile(rmfile)

		### run batchboxer
		self.boxedpartdatas, self.imgstackfile, self.partmeantree = self.boxParticlesFromImage(imgdata)
		if self.boxedpartdatas is None:
			apDisplay.printWarning("no particles were boxed from "+shortname+"\n")
			self.badprocess = True
			return

		self.stats['lastpeaks'] = len(self.boxedpartdatas)

		apDisplay.printMsg("do not break function now otherwise it will corrupt run")
		time.sleep(1.0)

		### merge image particles into big stack
		totalpart = self.mergeImageStackIntoBigStack(self.imgstackfile, imgdata)

		### check if particle limit is met
		if self.params['partlimit'] is not None and totalpart > self.params['partlimit']:
			apDisplay.printWarning("reached particle number limit of "+str(self.params['partlimit'])+" now stopping")
			self.imgtree = []
			self.notdone = False

	#=======================
	def postLoopFunctions(self):
		### Delete CTF corrected images
		if self.params['keepall'] is False:
			pattern = os.path.join(self.params['rundir'], self.params['sessionname']+'*.dwn.mrc')
			apFile.removeFilePattern(pattern)
		### Averaging completed stack
		stackpath = os.path.join(self.params['rundir'], "start.hed")
		apStack.averageStack(stack=stackpath)
		### Create Stack Mean Plot
		if self.params['commit'] is True and self.params['meanplot'] is True:
			stackid = apStack.getStackIdFromPath(stackpath)
			if stackid is not None:
				apStackMeanPlot.makeStackMeanPlot(stackid)
		apDisplay.printColor("Timing stats", "blue")
		self.printTimeStats("Batch Boxer", self.batchboxertimes)
		self.printTimeStats("Ctf Correction", self.ctftimes)
		self.printTimeStats("Stack Merging", self.mergestacktimes)
		self.printTimeStats("Mean/Std Read", self.meanreadtimes)
		self.printTimeStats("DB Insertion", self.insertdbtimes)

	#=======================
	def printTimeStats(self, name, timelist):
		if len(timelist) < 2:
			return
		meantime = self.stats['timesum']/float(self.stats['count'])
		timearray = numpy.array(timelist, dtype=numpy.float64)
		apDisplay.printColor("%s: %s (%.2f percent)"%
			(name, apDisplay.timeString(timearray.mean(), timearray.std()), 100*timearray.mean()/meantime), "blue")

	#=======================
	def commitToDatabase(self, imgdata):
		t0 = time.time()
		### loop over the particles and insert
		for i in range(len(self.boxedpartdatas)):
			partdata = self.boxedpartdatas[i]
			partmeandict = self.partmeantree[i]

			self.particleNumber += 1
			stpartq = appionData.ApStackParticlesData()

			### check unique params
			stpartq['stack'] = self.stackdata
			stpartq['stackRun'] = self.stackrundata
			stpartq['particleNumber'] = self.particleNumber
			stpartdata = stpartq.query(results=1)
			if stpartdata:
				apDisplay.printError("trying to insert a duplicate particle")

			stpartq['particle'] = partdata
			stpartq['mean'] = partmeandict['mean']
			stpartq['stdev'] = partmeandict['stdev']
			if self.params['commit'] is True:
				stpartq.insert()
		self.insertdbtimes.append(time.time()-t0)

		### last remove any existing boxed files, reset global params
		shortname = apDisplay.short(imgdata['filename'])
		shortfileroot = os.path.join(self.params['rundir'], shortname)
		rmfiles = glob.glob(shortfileroot+"*")
		for rmfile in rmfiles:
			apFile.removeFile(rmfile)
		self.imgstackfile = None
		self.boxedpartdatas = []


if __name__ == '__main__':
	makeStack = Makestack2Loop()
	makeStack.run()



