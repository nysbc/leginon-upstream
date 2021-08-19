import subprocess
import json
import os
import multiprocessing
import time

from leginon import leginondata
from leginon import mosaictargetfinder
import gui.wx.MosaicClickTargetFinder

def pointInPolygon(x,y,poly):
	'''
	Ray tracing method from https://stackoverflow.com/questions/36399381/whats-the-fastest-way-of-checking-if-a-point-is-inside-a-polygon-in-python
	'''
	n = len(poly)
	inside = False
	p1x,p1y = poly[0]
	for i in range(n+1):
		p2x,p2y = poly[i % n] #even ?
		if y > min(p1y,p2y):
			if y <= max(p1y,p2y):
				if x <= max(p1x,p2x):
					if p1y != p2y:
						# x intercept
						xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
					if p1x == p2x or x <= xints:
						inside = not inside
		p1x,p1y = p2x,p2y
	return inside

def pointsInBlobs(blobs, points):
	if len(blobs) == 0:
		return []
	has_point =  map((lambda x: False), blobs)
	if len(points) == 0:
		return has_point
	total_points = len(points)
	total = 0
	for i, b in enumerate(blobs):
		result_map = map(lambda x: pointInPolygon(x[1],x[0],b.vertices), points)
		if max(result_map):
			total += 1
			has_point[i] = True
			if total == total_points:
					break
	return has_point

class StatsBlob(object):
	def __init__(self, info_dict, index):
		'''Simple blob object with image and stats as attribute
			center = (row, col) on image
		'''
		mean = info_dict['brightness']
		stddev = 1.0
		size = info_dict['area']
		score = info_dict['score']
		center = info_dict['center'][1],info_dict['center'][0]
		vertices = info_dict['vertices']
		self.center_modified = False
		self.stats = {"label_index": index, "center":center, "n":size, "size":size, "mean":mean, "score":score, "stddev":score}
		self.vertices = vertices
		self.info_dict = info_dict

class MosaicTargetFinderBase(mosaictargetfinder.MosaicClickTargetFinder):
	panelclass = gui.wx.MosaicClickTargetFinder.Panel
	settingsclass = leginondata.MosaicClickTargetFinderSettingsData
	defaultsettings = dict(mosaictargetfinder.MosaicClickTargetFinder.defaultsettings)

	eventoutputs = mosaictargetfinder.MosaicClickTargetFinder.eventoutputs
	targetnames = mosaictargetfinder.MosaicClickTargetFinder.targetnames

	def __init__(self, id, session, managerlocation, **kwargs):
		super(MosaicTargetFinderBase, self).__init__(id, session, managerlocation, **kwargs)
		self.start()
		self.ext_blobs ={}

	def findSquareBlobs(self):
		# Scale to smaller finder size
		# TODO where did this call to ?
		self.scaleFinderMosaicImage()
		if self.mosaicimagedata and 'filename' in self.mosaicimagedata.keys():
			mosaic_image_path = os.path.join(self.session['image path'],self.mosaicimagedata['filename']+'.mrc')
			self.logger.info('running external square finding')
			blobs = self._runExternalBlobFinder(self.mosaicimagedata['image'],mosaic_image_path)
			# show blob target and stats
			return self.ext_blobs['all']
		return []

	def getOutPath(self, label):
		job_basename = self.getJobBasename(label)
		outpath = os.path.join(self.session['image path'],'%s.json' % job_basename)
		return outpath

	def getJobBasename(self, label):
		return '%s_%s' % (self.session['name'], label)

	def _runExternalBlobFinder(self, imagearray, mosaic_image_path,label='all'):
		outdir = os.path.dirname(mosaic_image_path)
		job_basename = self.getJobBasename(label)
		outpath = os.path.join(outdir, '%s.json' % job_basename)
		if os.path.isfile(outpath):
			os.remove(outpath)
		# This process must create the output json at outpath
		cmd = 'source /Users/acheng/sq_finding.sh %s %s %s' % (job_basename, mosaic_image_path, outdir)
		proc = subprocess.Popen(cmd, shell=True)
		proc.wait()

	def loadBlobs(self, label, outpath):
		if not os.path.isfile(outpath):
			self.logger.warning("external square finding did not run")
			self.ext_blobs[label] = []
			return
		f = open(outpath,'r')
		# returns one line
		line = f.readlines()[0]
		blob_dicts = json.loads(line)
		blobs = []
		for n, b in enumerate(blob_dicts):
			blobs.append(StatsBlob(b, n)) # (row, col)
		self.ext_blobs[label] = blobs

	def filterPoints(self, blobs, example_points, panel_points):
		'''
		Return boolean for each blob.
		has_priority: at least one example_point is in the blob
		to_avoid: at least one panel_point is in the blob
		display_array: some image array to display in the gui as Thresholded image.
		'''
		return self.filterPointsByVertices(self.finder_blobs, example_points, panel_points)

	def filterPointsByVertices(self, blobs, example_points, panel_points):
		has_priority = pointsInBlobs(blobs, example_points)
		to_avoid = pointsInBlobs(blobs, panel_points)
		return has_priority, to_avoid, None

	def setFilterSettings(self, example_blobs):
		if example_blobs:
			# use the stats of the example blobs
			means = map((lambda x: x.stats['mean']), example_blobs)
			mean_min = min(means)
			mean_max = max(means)
			stddevs = map((lambda x: x.stats['score']), example_blobs)
			score_min = min(stddevs)
			score_max = max(stddevs)
			sizes = map((lambda x: x.stats['n']), example_blobs)
			size_min = min(sizes)
			size_max = max(sizes)
			self.settings['blobs']['min mean'] = mean_min
			self.settings['blobs']['max mean'] = mean_max
			self.settings['blobs']['min stdev'] = score_min # TODO name it correctly
			self.settings['blobs']['max stdev'] = score_max
			self.settings['blobs']['min filter size'] = size_min
			self.settings['blobs']['max filter size'] = size_max
			self.setSettings(self.settings, False)
			return

	def filterStats(self, blobs):	
		'''
		filter based on blob stats
		'''
		prefs = self.storeSquareFinderPrefs()
		mean_min = self.settings['blobs']['min mean']-0.0005 # rounding precision
		mean_max = self.settings['blobs']['max mean']+0.0005
		score_min = self.settings['blobs']['min stdev']
		score_max = self.settings['blobs']['max stdev']
		size_min = self.settings['blobs']['min filter size']
		size_max = self.settings['blobs']['max filter size']
		good_blobs = []
		for blob in blobs:
			row = blob.stats['center'][0]
			column = blob.stats['center'][1]
			mean = blob.stats['mean']
			std = blob.stats['score']
			size = blob.stats['n']
			#if (mean_min <= mean <= mean_max) and (score_min <= std <= score_max) and (size_min <= size <= size_max):
			if (mean_min <= mean <= mean_max) and (size_min <= size <= size_max):
				good_blobs.append(blob)
			else:
				stats = leginondata.SquareStatsData(prefs=prefs, row=row, column=column, mean=mean, stdev=std)
				stats['good'] = False
				# only publish bad stats
				self.publish(stats, database=True)
		return good_blobs

class MosaicClickTargetFinder(MosaicTargetFinderBase):
	panelclass = gui.wx.MosaicClickTargetFinder.Panel
	settingsclass = leginondata.MosaicClickTargetFinderSettingsData
	defaultsettings = dict(mosaictargetfinder.MosaicClickTargetFinder.defaultsettings)

	eventoutputs = mosaictargetfinder.MosaicClickTargetFinder.eventoutputs
	targetnames = mosaictargetfinder.MosaicClickTargetFinder.targetnames

	def __init__(self, id, session, managerlocation, **kwargs):
		super(MosaicClickTargetFinder, self).__init__(id, session, managerlocation, **kwargs)
		self.tileblobmap = {}
		self.finder_blobs = []
		self.start()
		self.p = {}

	def _addTile(self, imagedata):
		super(MosaicClickTargetFinder, self)._addTile(imagedata)
		mrcpath = os.path.join(imagedata['session']['image path'], imagedata['filename']+'.mrc')
		imid = imagedata.dbid
		label = '%d' % imid
		self.logger.info('running external square finding on imgid=%d' % imid)
		job_basename = self.getJobBasename(label)
		self.p[imid] = multiprocessing.Process(target=self._runExternalBlobFinder, args=(imagedata['image'], mrcpath,label))
		self.p[imid].start()

	def createMosaicImage(self):
		super(MosaicClickTargetFinder, self).createMosaicImage()
		if self.mosaic and self.tileblobmap and self.finder_scale_factor:
			self.finder_blobs = []
			s = self.finder_scale_factor
			for imid, targetlists in self.targetmap.items():
					tile = self.tilemap[imid]
					shape = tile.image.shape
					label = '%d' % imid
					if label in self.ext_blobs.keys():
						self.tileblobmap[imid] = self.ext_blobs[label]
						self.addFinderBlobs(tile, imid)

	def addFinderBlobs(self, tile, imid):
					s = self.finder_scale_factor
					for b in self.tileblobmap[imid]:
						#statistics are calculated on finder_mosaic
						vertices = map((lambda x: self._tile2MosaicPosition(tile, (x[1],x[0]*s), self.finder_mosaic)), b.vertices)
						r,c = self._tile2MosaicPosition(tile, b.stats['center'], self.finder_mosaic)
						new_info_dict = dict(b.info_dict)
						new_info_dict['vertices'] = map((lambda x: (x[1],x[0])),vertices)
						new_info_dict['center'] = c,r
						self.finder_blobs.append(StatsBlob(new_info_dict, len(self.finder_blobs)))

	def findSquareBlobs(self):
		imids = list(map((lambda x: int(x)),self.p.keys()))
		for imid in imids:
			self.p[imid].join()
			self.p[imid].terminate()
			self.p.pop(imid)
		new_imids = set(imids).difference(self.tileblobmap.keys())
		for imid in new_imids:
			label = '%d' % imid
			outpath = self.getOutPath(label)
			self.loadBlobs(label, outpath)
			self.tileblobmap[imid] = self.ext_blobs['%d' % imid]
			s = self.finder_scale_factor
			tile = self.tilemap[imid]
			self.addFinderBlobs(tile,imid)
		return list(self.finder_blobs)
