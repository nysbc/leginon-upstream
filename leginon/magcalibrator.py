#
# COPYRIGHT:
#	   The Leginon software is Copyright 2003
#	   The Scripps Research Institute, La Jolla, CA
#	   For terms of the license agreement
#	   see  http://ami.scripps.edu/software/leginon-license
#
import calibrator
import calibrationclient
import event
import leginondata
import node
import gui.wx.MagCalibrator
import time
import libCV
import numpy
from pyami import arraystats, mrc, affine, msc
from scipy import ndimage

class MagCalibrator(calibrator.Calibrator):
	'''
	'''
	panelclass = gui.wx.MagCalibrator.Panel
	settingsclass = leginondata.MagCalibratorSettingsData
	defaultsettings = calibrator.Calibrator.defaultsettings
	defaultsettings.update({
		'minsize': 50,
		'maxsize': 500,
		'pause': 1.0,
	})
	def __init__(self, id, session, managerlocation, **kwargs):
		calibrator.Calibrator.__init__(self, id, session, managerlocation, **kwargs)
		self.start()

	def uiStart(self):
		mag = self.instrument.tem.Magnification
		print 'MAG', mag
		mags = self.getMags()
		print 'MAGS', mags
		magindex = mags.index(mag)
		othermag = mags[magindex-1]
		self.compareToOtherMag(othermag)
		return
		print 'MAGINDEX', magindex
		if magindex == 0:
			print 'already at lowest mag'
			return
		else:
			previousmags = mags[magindex-5:magindex-1]
			previousmags.reverse()
			print 'PREVIOUSMAGS', previousmags
	
		self.matchMags(previousmags)

	def uiTest(self):
		imdata = self.acquireImage()
		im = imdata['image']
		regions = self.findRegions(im)

	def pause(self):
		pause = self.settings['pause']
		time.sleep(pause)

	def getMags(self):
		mags = self.instrument.tem.Magnifications
		return mags

	def compareToOtherMag(self, othermag):
		## acquire image at this mag
		thisimagedata = self.acquireImage()
		stats = arraystats.all(thisimagedata['image'])
		limitmax = 1.5 * stats['mean']
		limitmin = 0.5 * stats['mean']
		thismag = self.instrument.tem.Magnification
		print 'THISMAG', thismag
		print 'OTHERMAG', othermag

		## acquire image at other mag
		self.instrument.tem.Magnification = othermag
		self.pause()
		otherimagedata = self.acquireWithinRange(3000, 40000)
		this = thisimagedata['image']
		other = otherimagedata['image']
		
		## compare
		anglestart = -3
		angleend = 3
		angleinc = 0.25
		scaleguess = float(othermag) / thismag
		scalestart = scaleguess - 0.08
		scaleend = scaleguess + 0.08
		scaleinc = 0.02
		prebin = 4
		result = msc.findRotationScaleShift(this, other, anglestart, angleend, angleinc, scalestart, scaleend, scaleinc, prebin)
		if result is None:
			self.logger.error('could not determine relation')
			return

		angle = result[0]
		scale = result[1]
		shift = result[2]
		print 'ANGLE', angle
		print 'SCALE', scale
		print 'SHIFT', shift
		magdata = leginondata.MagnificationComparisonData()
		magdata['maghigh'] = thismag
		magdata['maglow'] = othermag
		magdata['rotation'] = angle
		magdata['scale'] = scale
		magdata['shiftrow'] = shift[0]
		magdata['shiftcol'] = shift[1]
		magdata.insert(force=True)

	def acquireWithinRange(self, min, max):
		imagedata = self.acquireImage()
		mean = arraystats.mean(imagedata['image'])
		self.logger.info('image mean:  %f' % (mean,))

		while mean > max:
			self.logger.info('too bright, spreading beam...')
			# assuming we are greater than crossover, increase lens value
			i = self.instrument.tem.Intensity
			self.instrument.tem.Intensity = 1.1 * i
			imagedata = self.acquireImage()
			mean = arraystats.mean(imagedata['image'])
			self.logger.info('image mean:  %f' % (mean,))

		while mean < min:
			self.logger.info('not bright enough, condensing beam...')
			# assuming we are greater than crossover, decrease lens value
			i = self.instrument.tem.Intensity
			self.instrument.tem.Intensity = 0.9 * i
			imagedata = self.acquireImage()
			mean = arraystats.mean(imagedata['image'])
			self.logger.info('image mean:  %f' % (mean,))

		return imagedata

	def acquireImage(self):
		im = calibrator.Calibrator.acquireImage(self)
		im['image'] = ndimage.gaussian_filter(im['image'], 1.2)
		return im

	def matchMags(self, mags):
		# acquire first image at current state
		oldimagedata = self.acquireImage()
		self.findRegions(oldimagedata['image'])
		mrc.write(oldimagedata['image'], 'imref.mrc')
		stats = arraystats.all(oldimagedata['image'])
		shape = oldimagedata['image'].shape

		# determine limits to adjust exposure of other mags
		limitmax = 1.5 * stats['mean']
		limitmin = 0.5 * stats['mean']
		self.logger.info('image1 mean:  %f, limits:  %f-%f' % (stats['mean'], limitmin, limitmax))

		## iterate through mags
		runningresult = numpy.identity(3)
		for i,mag in enumerate(mags):
			self.instrument.tem.Magnification = mag
			self.pause()

			newimagedata = self.acquireWithinRange(limitmin, limitmax)
			self.findRegions(newimagedata['image'])
			mrc.write(newimagedata['image'], 'im%02d.mrc' % (i,))

			minsize = self.settings['minsize']
			maxsize = self.settings['maxsize']
			self.logger.info('matchimages')
			result = self.matchImages(oldimagedata['image'], newimagedata['image'], minsize, maxsize)
			runningresult = numpy.dot(result, runningresult)
			self.logger.info('transforms')
			final_step = affine.transform(newimagedata['image'], result, shape)
			final_all = affine.transform(newimagedata['image'], runningresult, shape)
			self.logger.info('writing result mrcs')
			mrc.write(final_step, 'trans%02d.mrc' % (i,))
			mrc.write(final_all, 'transall%02d.mrc' % (i,))
			oldimagedata = newimagedata

#			self.getMagDiff(imagedata1, imagedata2, result)

	def getMagDiff(self, imdata1, imdata2, matrix):
		ccol = imdata1['camera']['dimension']['x'] / 2 - 0.5
		crow = imdata1['camera']['dimension']['y'] / 2 - 0.5
		center = numpy.array((ccol, crow, 1))
		othercenter = numpy.dot(matrix, center)
		print 'OTHER', othercenter

	def matchImages(self, im1, im2, minsize, maxsize):
		result = libCV.MatchImages(im1, im2, minsize, maxsize, 0, 0, 1, 1)
		return result

	def findRegions(self, im):
		minsize = self.settings['minsize']
		maxsize = self.settings['maxsize']
		regions, image = libCV.FindRegions(im, minsize, maxsize, 0, 0, 1, 1)
		coords = map(self.regionCenter, regions)
		self.setTargets(coords, 'Peak')
		return regions

	def regionCenter(self, region):
		coord = region['regionEllipse'][:2]
		coord = coord[1], coord[0]
		return coord
