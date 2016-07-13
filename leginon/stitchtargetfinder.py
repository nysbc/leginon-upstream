# The Leginon software is Copyright 2004
# The Scripps Research Institute, La Jolla, CA
# For terms of the license agreement
# see http://ami.scripps.edu/software/leginon-license
#
# $Revision: 1.8 $
# $Name: not supported by cvs2svn $
# $Date: 2007-05-21 23:17:17 $
# $Author: pulokas $
# $State: Exp $
# $Locker:  $

import os.path
import threading
import numpy
import math
from leginon import leginondata
from leginon import raster
from pyami import mrc
from leginon import targetfinder
import gui.wx.StitchTargetFinder

class StitchTargetFinder(targetfinder.TargetFinder):
	panelclass = gui.wx.StitchTargetFinder.Panel
	settingsclass = leginondata.StitchTargetFinderSettingsData
	defaultsettings = dict(targetfinder.TargetFinder.defaultsettings)
	defaultsettings.update({
		'test image': '',
		'overlap': 0.0,
		'coverage': 2.0,
	})
	def __init__(self, *args, **kwargs):
		self.userpause = threading.Event()
		targetfinder.TargetFinder.__init__(self, *args, **kwargs)
		self.start()

	def readImage(self, filename):
		# convert to float
		image2 = mrc.read(filename)
		image = numpy.asarray(image2,dtype=numpy.float)
		
		if image.any():
			self.setImage(image, 'Image')
		else:
			self.logger.error('Can not load image')

	def stitchFindTargets(self):
		shape = self.currentimagedata['image'].shape
		half = ( shape[0] / 2, shape[1] / 2 )
		spacing = min(shape) *(1-self.settings['overlap']*0.01)
		diameter = min(shape) * self.settings['coverage']
		limit = math.ceil(diameter/spacing)
		anglerad = 0
		odd_indices = raster.createIndices2(limit/2.0,limit/2.0,anglerad,'ellipse')
		even_indices = raster.createIndices((int(limit),int(limit)))

		if len(odd_indices) < len(even_indices):
			goodindices = odd_indices
		else:
			goodindices = even_indices
		rasterpoints = raster.createRaster3(spacing, anglerad, goodindices)
		rasterpoints = map((lambda x: (x[0]+half[0],x[1]+half[0])),rasterpoints)
		
		self.setTargets(rasterpoints, 'acquisition')
		# This sleep gives database time to save the targets
		import time
		time.sleep(1)

		if self.settings['user check']:
			self.panel.foundTargets()

	def findTargets(self, imdata, targetlist):
		# convert to float
		image2 = imdata['image']
		image = numpy.asarray(image2,dtype=numpy.float)
		
		self.setImage(image, 'Image')

		self.stitchFindTargets()

		if self.settings['user check']:
			# user now clicks on targets
			self.notifyUserSubmit()
			self.userpause.clear()
			self.setStatus('user input')
			self.userpause.wait()

		self.setStatus('processing')

		self.publishTargets(imdata, 'acquisition', targetlist)

		self.logger.info('Targets have been submitted')

	def testTargeting(self):
		self.stitchFindTargets()
