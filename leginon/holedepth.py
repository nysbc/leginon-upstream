#!/usr/bin/env python

#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

import data
import targetfinder
import holefinder
import holedepthback
import Mrc
import newdict
import threading
import ice
import instrument
import os.path
import calibrationclient as calclient
try:
	import numarray as Numeric
except:
	import Numeric
import gui.wx.HoleDepth

class HoleDepth(holefinder.HoleFinder):
	panelclass = gui.wx.HoleDepth.Panel
	settingsclass = data.HoleDepthFinderSettingsData
	defaultsettings = dict(holefinder.HoleFinder.defaultsettings)
	defaultsettings.update({
		'skip': False,
		'Hole Untilt filename': '',
		'Hole Tilt filename': '',
		'I filename': '',
		'I0 filename': '',
		'edge lpf': {
			'sigma': 1.0,
		},
		'edge': True,
		'edge type': 'sobel',
		'edge log size': 9,
		'edge log sigma': 1.4,
		'edge absolute': False,
		'edge threshold': 100.0,
		'template rings': [(30, 40)],
		'template type': 'cross',
		'template lpf': {
			'sigma': 1.0,
		},
		'tilt axis': 0.0,
		'threshold': 3.0,
		'blobs border': 20,
		'blobs max': 300,
		'blobs max size': 1000,
#		'pickhole center': [(100, 100)],
		'pickhole radius': 15.0,
		'pickhole zero thickness': 1000.0,
	})
	def __init__(self, id, session, managerlocation, **kwargs):
		holefinder.HoleFinder.__init__(self, id, session, managerlocation, **kwargs)
		self.hf = holedepthback.HoleFinder()
		self.pclient = calclient.PixelSizeCalibrationClient(self)
		self.hdimagedata = {	
		'Hole Untilt filename': None,
		'Hole Tilt filename': None,
		'I filename': None,
		'I0 filename': None,
		}
		self.holedepth = {
		'Hole Tilt filename': None,
		}

	def readImage(self,filename,imagetype=None):
		imagedata = self.getImageFromDB(filename)
		if imagedata is None:
			try:
				orig = Mrc.mrc_to_numeric(filename)
				self.logger.exception('Read image not in session')
			except Exception, e:
				self.logger.exception('Read image failed: %s' % e[-1])
				return
		else:
			orig = imagedata['image']
			tltangle = imagedata['scope']['stage position']['a']
			imagebin = imagedata['camera']['binning']['x']
			imagemag = imagedata['scope']['magnification']
			imagecamera = imagedata['camera']['ccdcamera']
			imagetem = imagedata['scope']['tem']
			pixelsize = self.pclient.retrievePixelSize(imagetem,imagecamera,imagemag)
			binnedpixel=imagebin*pixelsize
		self.currentimagedata = imagedata
		self.currentimagetype = imagetype
		self.hdimagedata[self.currentimagetype] = imagedata
		self.hf['original'] = orig
		self.setImage(orig,'Original')
		self.hf.configure_template(tilt_angle=tltangle)
		self.hf.configure_distance(binned_pixel=binnedpixel)

	def findEdges(self):
		self.logger.info('find edges')
		n = self.settings['edge log size']
		sig = self.settings['edge log sigma']
		ab = self.settings['edge absolute']
		edges = self.settings['edge']
		filt = self.settings['edge type']
		lpfsettings = self.settings['edge lpf']
		lowpasssig = lpfsettings['sigma']
		edgethresh = self.settings['edge threshold']
		self.hf.configure_edges(filter=filt, size=n, sigma=sig, absvalue=ab, lpsig=lowpasssig, thresh=edgethresh, edges=edges)
		self.hf.find_edges()
		# convert to Float32 to prevent seg fault
		self.setImage(self.hf['edges'].astype(Numeric.Float32), 'Edge')

	def correlateTemplate(self):
		self.logger.info('correlate ring template')
		ringlist = self.settings['template rings']
		tltaxis = self.settings['tilt axis']
		# convert diameters to radii
		radlist = []
		for ring in ringlist:
			radring = (ring[0] / 2.0, ring[1] / 2.0)
			radlist.append(radring)
		self.hf.configure_template(ring_list=radlist,tilt_axis=tltaxis)
		self.hf.create_template()
		cortype = self.settings['template type']
		lpfsettings = self.settings['template lpf']
		corsigma = lpfsettings['sigma']
		if cortype == 'phase' and corsigma:
			corfilt = (corsigma,)
		else:
			corfilt = None
		self.hf.configure_correlation(cortype, corfilt)
		self.hf.correlate_template()
		self.setImage(self.hf['correlation'].astype(Numeric.Float32), 'Template')

	def threshold(self):
		self.logger.info('threshold')
		tvalue = self.settings['threshold']
		self.hf.configure_threshold(tvalue)
		self.hf.threshold_correlation()
		# convert to Float32 to prevent seg fault
		self.setImage(self.hf['threshold'].astype(Numeric.Float32), 'Threshold')

	def blobCenters(self, blobs):
		centers = []
		for blob in blobs:
			c = tuple(blob.stats['center'])
			centers.append((c[1],c[0]))
		return centers

	def blobStatsTargets(self, blobs):
		targets = []
		for blob in blobs:
			target = {}
			target['x'] = blob.stats['center'][1]
			target['y'] = blob.stats['center'][0]
			target['stats'] = newdict.OrderedDict()
			target['stats']['Size'] = blob.stats['n']
			target['stats']['Mean'] = blob.stats['mean']
			target['stats']['Std. Dev.'] = blob.stats['stddev']
			targets.append(target)
		return targets

	def findBlobs(self):
		self.logger.info('find blobs')
		border = self.settings['blobs border']
		blobsize = self.settings['blobs max size']
		maxblobs = self.settings['blobs max']
		self.hf.configure_blobs(border=border, maxblobsize=blobsize, maxblobs=maxblobs)
		self.hf.find_blobs()

		holedepth=self.hf.find_distance()
		self.holedepth[self.currentimagetype]=holedepth
		holedepthnm=holedepth*(1e9)

		blobs = self.hf['blobs']
		#centers = self.blobCenters(blobs)
		targets = self.blobStatsTargets(blobs)
		#self.logger.info('Number of blobs: %s' % (len(centers),))
		self.logger.info('Number of blobs: %s' % (len(targets),))
		self.logger.info('Calculated Hole Depth: %.1f nm' % (holedepthnm,))
		#self.setTargets(centers, 'Blobs')
		self.setTargets(targets, 'Blobs')

	def holeStatsTargets(self, holes):
		targets = []
		for hole in holes:

			mean = float(hole.stats['hole_mean'])
			tmean = self.icecalc.get_thickness(mean)
			std = float(hole.stats['hole_std'])
			tstd = self.icecalc.get_stdev_thickness(std, mean)

			target = {}
			target['x'] = hole.stats['center'][1]
			target['y'] = hole.stats['center'][0]
			target['stats'] = newdict.OrderedDict()
			target['stats']['Mean Intensity'] = mean
			target['stats']['Mean Thickness'] = tmean
			target['stats']['S.D. Intensity'] = std
			target['stats']['S.D. Thickness'] = tstd
			targets.append(target)
		return targets

	def getPickHoleStats(self,holecenters):
		self.logger.info('pickhole stats')
		
		r = self.settings['pickhole radius']
		i0 = self.settings['pickhole zero thickness']
		self.icecalc.set_i0(i0)

		self.hf.configure_pickhole(center_list=holecenters)

		self.hf.configure_holestats(radius=r)
		self.hf.calc_holestats()

		holes = self.hf['holes']
		
		targets = self.holeStatsTargets(holes)
		self.logger.info('Number of picked holes: %s' % (len(targets),))
		self.setTargets(targets, 'PickHoles')

	def storeK(self):
		hfprefs = self.storeHoleDepthFinderPrefsData(self.currentimagedata,self.hdimagedata)
		self.storeHoleDepthStatsData(hfprefs)


	def everything(self):
		# find edges
		self.findEdges()
		# correlate template
		self.correlateTemplate()
		# threshold
		self.threshold()
		# find blobs
		self.findBlobs()
		# lattice
		self.fitLattice()
		# ice
		self.storeK()


	def storeHoleDepthStatsData(self, prefs):
		holes = self.hf['holes']
		targets = self.holeStatsTargets(holes)
		depth = self.holedepth['Hole Tilt filename']

		for target in targets:
			stats=target['stats']
			holestats = data.HoleDepthStatsData(session=self.session, prefs=prefs)
			holestats['row'] = target['y']
			holestats['column'] = target['x']
			holestats['mean'] = stats['Mean Intensity']
			holestats['thickness-mean'] = stats['Mean Thickness']
			holestats['holedepth'] = depth

			self.publish(holestats, database=True)

	def storeHoleDepthFinderPrefsData(self, imagedata,allhdimagedata):
		hfprefs = data.HoleDepthFinderPrefsData()
		
		hfprefs.update({
			'session': self.session,

			'untilt-hole-image': allhdimagedata['Hole Untilt filename'],
			'tilt-hole-image': allhdimagedata['Hole Tilt filename'],
			'I-image': allhdimagedata['I filename'],
			'I0-image': allhdimagedata['I0 filename'],

			'image': imagedata,
			'edge-lpf-sigma': self.settings['edge lpf']['sigma'],
			'edge-filter-type': self.settings['edge type'],
			'edge-threshold': self.settings['edge threshold'],

			'template-rings': self.settings['template rings'],
			'template-correlation-type': self.settings['template type'],
			'template-lpf': self.settings['template lpf']['sigma'],

			'template-tilt-axis': self.settings['tilt axis'],

			'threshold-value': self.settings['threshold'],
			'blob-border': self.settings['blobs border'],
			'blob-max-number': self.settings['blobs max'],
			'blob-max-size': self.settings['blobs max size'],
			'stats-radius': self.settings['pickhole radius'],
			'ice-zero-thickness': self.settings['pickhole zero thickness'],

		})

		self.publish(hfprefs, database=True)
		return hfprefs

	def findTargets(self, imdata, targetlist):
		self.setStatus('processing')

		## auto or not?
		self.hf['original'] = imdata['image']
		self.currentimagedata = imdata
		self.setImage(imdata['image'], 'Original')
		if self.settings['skip']:
			self.bypass()
		else:
			self.everything()

		## user part
		if self.settings['user check']:
			self.setStatus('user input')
			self.logger.info('Waiting for user to check targets...')
			self.panel.submitTargets()
			self.userpause.clear()
			self.userpause.wait()
			self.panel.targetsSubmitted()
			self.setStatus('processing')

		self.logger.info('Publishing targets...')
		### publish targets from goodholesimage
		self.publishTargets(imdata, 'focus', targetlist)
		self.publishTargets(imdata, 'acquisition', targetlist)
		self.setStatus('idle')

