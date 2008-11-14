#!/usr/bin/env python
#
import os
import time
import sys
import random
import math
import shutil
#appion
import appionScript
import apDisplay
import apAlignment
import apFile
import apTemplate
import apStack
import apEMAN
import apXmipp
from apSpider import alignment
import appionData

#=====================
#=====================
class MaximumLikelihoodScript(appionScript.AppionScript):

	#=====================
	def setupParserOptions(self):
		self.parser.set_usage("Usage: %prog --stack=ID [ --num-part=# ]")
		self.parser.add_option("-N", "--num-part", dest="numpart", type="int", default=3000,
			help="Number of particles to use", metavar="#")
		self.parser.add_option("-s", "--stack", dest="stackid", type="int",
			help="Stack database id", metavar="ID#")

		### radii
		self.parser.add_option("-m", "--mask", dest="maskrad", type="float",
			help="Mask radius for particle coran (in Angstoms)", metavar="#")
		self.parser.add_option("--lowpass", dest="lowpass", type="int",
			help="Low pass filter radius (in Angstroms)", metavar="#")
		self.parser.add_option("--bin", dest="bin", type="int", default=1,
			help="Bin images by factor", metavar="#")

		self.parser.add_option("--max-iter", dest="maxiter", type="int", default=100,
			help="Maximum number of iterations", metavar="#")
		self.parser.add_option("--num-classes", dest="numclasses", type="int",
			help="Number of classes to create", metavar="#")
		#self.parser.add_option("--templates", dest="templateids",
		#	help="Template Id for template init method", metavar="1,56,34")

		self.parser.add_option("-C", "--commit", dest="commit", default=True,
			action="store_true", help="Commit stack to database")
		self.parser.add_option("--no-commit", dest="commit", default=True,
			action="store_false", help="Do not commit stack to database")

		self.parser.add_option("-F", "--fast", dest="fast", default=True,
			action="store_true", help="Use fast method")
		self.parser.add_option("--no-fast", dest="fast", default=True,
			action="store_false", help="Do NOT use fast method")

		self.parser.add_option("-o", "--outdir", dest="outdir",
			help="Output directory", metavar="PATH")
		self.parser.add_option("-d", "--description", dest="description",
			help="Description of run", metavar="'TEXT'")
		self.parser.add_option("-n", "--runname", dest="runname",
			help="Name for this run", metavar="STR")

	#=====================
	def checkConflicts(self):
		if self.params['stackid'] is None:
			apDisplay.printError("stack id was not defined")
		#if self.params['description'] is None:
		#	apDisplay.printError("run description was not defined")
		if self.params['numclasses'] is None:
			apDisplay.printError("a number of classes was not provided")
		if self.params['runname'] is None:
			apDisplay.printError("run name was not defined")
		maxparticles = 15000
		if self.params['numpart'] > maxparticles:
			apDisplay.printError("too many particles requested, max: " 
				+ str(maxparticles) + " requested: " + str(self.params['numpart']))
		stackdata = apStack.getOnlyStackData(self.params['stackid'], msg=False)
		stackfile = os.path.join(stackdata['path']['path'], stackdata['name'])
		if self.params['numpart'] > apFile.numImagesInStack(stackfile):
			apDisplay.printError("trying to use more particles "+str(self.params['numpart'])
				+" than available "+str(apFile.numImagesInStack(stackfile)))

	#=====================
	def setOutDir(self):
		self.stackdata = apStack.getOnlyStackData(self.params['stackid'], msg=False)
		path = self.stackdata['path']['path']
		uppath = os.path.abspath(os.path.join(path, "../.."))
		self.params['outdir'] = os.path.join(uppath, "maxlike", self.params['runname'])

	#=====================
	def start(self):
		self.appiondb.dbd.ping()
		self.stack = {}
		self.stack['data'] = apStack.getOnlyStackData(self.params['stackid'])
		self.stack['apix'] = apStack.getStackPixelSizeFromStackId(self.params['stackid'])
		self.stack['part'] = apStack.getOneParticleFromStackId(self.params['stackid'])
		self.stack['boxsize'] = apStack.getStackBoxsize(self.params['stackid'])
		self.stack['file'] = os.path.join(self.stack['data']['path']['path'], self.stack['data']['name'])

		### convert stack into single spider files
		partlistdocfile = apXmipp.breakupStackIntoSingleFiles(self.stack['file'])

		### run the alignment
		self.appiondb.dbd.ping()
		aligntime = time.time()
		xmippcmd = ( "xmipp_ml_align2d "
			+" -i "+partlistdocfile
			+" -nref "+str(self.params['numclasses'])
			+" -iter "+str(self.params['maxiter'])
		)
		if self.params['fast'] is True:
			xmippcmd += " -fast "
		apEMAN.executeEmanCmd(xmippcmd, verbose=True)
		self.appiondb.dbd.ping()
		aligntime = time.time() - aligntime
		apDisplay.printMsg("Alignment time: "+apDisplay.timeString(aligntime))

		### remove large, worthless stack
		#spiderstack = os.path.join(self.params['outdir'], "start.spi")
		#apDisplay.printMsg("Removing un-aligned stack: "+spiderstack)
		#apFile.removeFile(spiderstack, warn=False)

		### do correspondence analysis
		corantime = time.time()
		#if not self.params['skipcoran']:
		#	maskpixrad = self.params['maskrad']/self.stack['apix']/self.params['bin']
		#	boxsize = int(math.floor(self.stack['boxsize']/self.params['bin']))
		#	self.appiondb.dbd.ping()
		#	self.contriblist = alignment.correspondenceAnalysis( alignedstack, 
		#		boxsize=boxsize, maskpixrad=maskpixrad, 
		#		numpart=self.params['numpart'], numfactors=self.params['numfactors'])
		#	self.appiondb.dbd.ping()
		#	### make dendrogram
		#	alignment.makeDendrogram(alignedstack, numfactors=self.params['numfactors'])
		corantime = time.time() - corantime


		inserttime = time.time()
		if self.params['commit'] is True:
			self.runtime = corantime + aligntime
			#self.insertMaxLikeRun(insert=True)
		else:
			apDisplay.printWarning("not committing results to DB")
		inserttime = time.time() - inserttime

		apDisplay.printMsg("Alignment time: "+apDisplay.timeString(aligntime))
		apDisplay.printMsg("Correspondence Analysis time: "+apDisplay.timeString(corantime))
		apDisplay.printMsg("Database Insertion time: "+apDisplay.timeString(inserttime))

#=====================
if __name__ == "__main__":
	maxLike = MaximumLikelihoodScript()
	maxLike.start()
	maxLike.close()


