#!/usr/bin/env python

import imagewatcher
import fftengine
import data
import Numeric
import cameraimage

class FFTViewer(imagewatcher.ImageWatcher):
	def __init__(self, id, nodelocations, **kwargs):
		imagewatcher.ImageWatcher.__init__(self, id, nodelocations, **kwargs)

		self.fftengine = fftengine.fftNumeric()

		self.defineUserInterface()
		self.start()

	def defineUserInterface(self):
		imwatch = imagewatcher.ImageWatcher.defineUserInterface(self)
		print 'imwatch', imwatch
		myspec = self.registerUISpec('ImViewer', ())
		print 'myspec', myspec
		myspec += imwatch

	def processData(self, imagedata):
		if not isinstance(imagedata, data.ImageData):
			print 'Data is not ImageData instance'
			return
		self.imagedata = imagedata

		numarray = imagedata['image']
		### calculate power image
		self.numarray = cameraimage.power(numarray)

		if self.popupvalue:
			self.clearAllTargetCircles()
			self.displayNumericArray()
