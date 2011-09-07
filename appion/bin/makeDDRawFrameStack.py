#!/usr/bin/env python

#pythonlib
import os
import sys
import math
#appion
from appionlib import appionLoop2
from appionlib import apDDprocess
from appionlib import apDisplay
from appionlib import apFile

class MakeRawFrameStackLoop(appionLoop2.AppionLoop):
	#=======================
	def setupParserOptions(self):
		self.parser.add_option("--rawarea", dest="rawarea", default=False,
			action="store_true", help="use full area of the raw frame, not leginon image area")
		self.parser.remove_option("--uncorrected")
		self.parser.remove_option("--reprocess")

	#=======================
	def checkConflicts(self):
		pass

	#=======================
	def preLoopFunctions(self):
		self.dd = apDDprocess.DirectDetectorProcessing()

	#=======================
	def processImage(self, imgdata):
		imgname = imgdata['filename']
		stackname = imgname+'_st.mrc'

		### first remove any existing stack file
		rundir = self.params['rundir']
		stackfilepath = os.path.join(rundir, stackname)
		apFile.removeFile(stackfilepath)

		### set processing image
		try:
			self.dd.setImageData(imgdata)
		except Exception, e:
			apDisplay.printWarning(e.message)
			return

		### run batchboxer
		self.dd.makeCorrectedRawFrameStack(rundir, self.params['rawarea'])

	def commitToDatabase(self, imgdata):
		pass

if __name__ == '__main__':
	makeStack = MakeRawFrameStackLoop()
	makeStack.run()



