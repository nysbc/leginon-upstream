#!/usr/bin/python -O

#python
import sys
import os
import random
import math
import time
import pprint
import cPickle
#site-packages
import numpy
from scipy import ndimage, stats
import MySQLdb
#appion
import appionScript
import apDisplay
import apStack
import apEulerCalc
import apParam
#sinedon
import sinedon

class satEulerScript(appionScript.AppionScript):
	def __init__(self):
		"""
		Need to connect to DB server before moving forward
		"""
		# connect
		self.dbconf = sinedon.getConfig('appionData')
		self.db     = MySQLdb.connect(**self.dbconf)
		# create a cursor
		self.cursor = self.db.cursor()
		appionScript.AppionScript.__init__(self)

	#=====================
	def getTiltRunIDFromReconID(self, reconid):
		t0 = time.time()
		query = (
			"SELECT \n"
			+"  part.`REF|ApSelectionRunData|selectionrun` AS tiltrunid \n"
			+"FROM `ApRefinementRunData` as refrun \n"
			+"LEFT JOIN `ApStackParticlesData` AS stackpart \n"
			+"  ON refrun.`REF|ApStackData|stack` = stackpart.`REF|ApStackData|stack` \n"
			+"LEFT JOIN `ApParticleData` AS part \n"
			+"  ON stackpart.`REF|ApParticleData|particle` = part.`DEF_id` \n"
			+"WHERE refrun.`DEF_id` = "+str(reconid)+" \n" 
			+"  LIMIT 1 \n"
		)
		self.cursor.execute(query)
		result = self.cursor.fetchall()
		#apDisplay.printMsg("Fetched data in "+apDisplay.timeString(time.time()-t0))
		if not result:
			apDisplay.printError("Failed to find tilt run")
		tiltrunid = result[0][0]
		apDisplay.printMsg("selected tilt run: "+str(tiltrunid))
		return tiltrunid

	#=====================
	def getLastIterationFromReconID(self, reconid):
		t0 = time.time()
		query = (
			"SELECT \n"
			+"  refdata.`iteration` \n"
			+"FROM `ApRefinementData` as refdata \n"
			+"WHERE refdata.`REF|ApRefinementRunData|refinementRun` = "+str(reconid)+" \n" 
			+"ORDER BY refdata.`iteration` DESC \n"
			+"LIMIT 1 \n"
		)
		self.cursor.execute(query)
		result = self.cursor.fetchall()
		#apDisplay.printMsg("Fetched data in "+apDisplay.timeString(time.time()-t0))
		if not result:
			apDisplay.printError("Failed to find any iterations")
		tiltrunid = result[0][0]
		apDisplay.printMsg("selected last iteration: "+str(tiltrunid))
		return tiltrunid

	#=====================
	def getEulersForIteration(self, reconid, tiltrunid, iteration=1):
		"""
		returns all classdata for a particular refinement iteration
		"""
		#get mirror and good/bad
		t0 = time.time()
		query = (
			"SELECT \n"
				+"  stpart1.particleNumber AS partnum1, \n"
				+"  e1.euler1 AS alt1, e1.euler2 AS az1, partclass1.`inplane_rotation` AS phi1, \n"
				+"  partclass1.`mirror` AS mirror1, partclass1.`thrown_out` AS reject1, \n"
				+"  stpart2.particleNumber AS partnum2, \n"
				+"  e2.euler1 AS alt2, e2.euler2 AS az2, partclass2.`inplane_rotation` AS phi2, \n"
				+"  partclass2.`mirror` AS mirror2, partclass2.`thrown_out` AS reject2 \n"
				+"FROM `ApTiltParticlePairData` AS tiltd \n"
				+"LEFT JOIN `ApImageTiltTransformData` as transform \n"
				+"  ON tiltd.`REF|ApImageTiltTransformData|transform`=transform.`DEF_id` \n"
				+"LEFT JOIN `ApStackParticlesData` AS stpart1 \n"
				+"  ON stpart1.`REF|ApParticleData|particle` = tiltd.`REF|ApParticleData|particle1` \n"
				+"LEFT JOIN `ApStackParticlesData` AS stpart2 \n"
				+"  ON stpart2.`REF|ApParticleData|particle` = tiltd.`REF|ApParticleData|particle2` \n"
				+"LEFT JOIN `ApParticleClassificationData` AS partclass1 \n"
				+"  ON partclass1.`REF|ApStackParticlesData|particle` = stpart1.`DEF_id` \n"
				+"LEFT JOIN `ApParticleClassificationData` AS partclass2 \n"
				+"  ON partclass2.`REF|ApStackParticlesData|particle` = stpart2.`DEF_id` \n"
				+"LEFT JOIN `ApEulerData` AS e1 \n"
				+"  ON partclass1.`REF|ApEulerData|eulers` = e1.`DEF_id` \n"
				+"LEFT JOIN `ApEulerData` AS e2 \n"
				+"  ON partclass2.`REF|ApEulerData|eulers` = e2.`DEF_id` \n"
				+"LEFT JOIN `ApRefinementData` AS refd1 \n"
				+"  ON partclass1.`REF|ApRefinementData|refinement` = refd1.`DEF_id` \n"
				+"LEFT JOIN `ApRefinementData` AS refd2 \n"
				+"  ON partclass2.`REF|ApRefinementData|refinement` = refd2.`DEF_id` \n"
				+"WHERE transform.`REF|ApSelectionRunData|tiltrun` = "+str(tiltrunid)+" \n"
				+"  AND refd1.`REF|ApRefinementRunData|refinementRun` = "+str(reconid)+" \n" 
				+"  AND refd1.`iteration` = "+str(iteration)+" \n"
				+"  AND refd2.`REF|ApRefinementRunData|refinementRun` = "+str(reconid)+" \n" 
				+"  AND refd2.`iteration` = "+str(iteration)+" \n"
				+"ORDER BY stpart1.particleNumber ASC \n"
				#+"LIMIT 10 \n"
			)
		#print query

		cachefile = "mysql_cache-recon"+str(reconid)+"-iter"+str(iteration)+".pickle"
		if not os.path.isfile(cachefile):
			apDisplay.printColor("Running MySQL query at "+time.asctime(), "yellow")
			self.cursor.execute(query)
			numrows = int(self.cursor.rowcount)
			apDisplay.printMsg("Found "+str(numrows)+" rows in "+apDisplay.timeString(time.time()-t0))
			apDisplay.printMsg("Fetching data at "+time.asctime())
			results = self.cursor.fetchall()
			cachef = open(cachefile, 'w', 0666)
			cPickle.dump(results, cachef)
		else:
			apDisplay.printColor("Using cached MySQL query data at "+time.asctime(), "cyan")
			cachef = open(cachefile, 'r')
			results = cPickle.load(cachef)
		apDisplay.printMsg("Fetched "+str(len(results))+" rows in "+apDisplay.timeString(time.time()-t0))
		return results

	#=====================
	def convertSQLtoEulerTree(self, results):
		t0 = time.time()
		eulertree = []
		for row in results:
			if len(row) < 11:
				apDisplay.printError("delete MySQL cache file and run again")
			try:
				eulerpair = { 'part1': {}, 'part2': {} }
				eulerpair['part1']['partid'] = int(row[0])
				eulerpair['part1']['euler1'] = float(row[1])
				eulerpair['part1']['euler2'] = float(row[2])
				eulerpair['part1']['euler3'] = float(row[3])
				eulerpair['part1']['mirror'] = self.nullOrValue(row[4])
				eulerpair['part1']['reject'] = self.nullOrValue(row[5])
				eulerpair['part2']['partid'] = int(row[6])
				eulerpair['part2']['euler1'] = float(row[7])
				eulerpair['part2']['euler2'] = float(row[8])
				eulerpair['part2']['euler3'] = float(row[9])
				eulerpair['part2']['mirror'] = self.nullOrValue(row[10])
				eulerpair['part2']['reject'] = self.nullOrValue(row[11])
				eulertree.append(eulerpair)
			except:
				print row
				apDisplay.printError("bad row entry")			

		apDisplay.printMsg("Converted "+str(len(eulertree))+" eulers in "+apDisplay.timeString(time.time()-t0))
		return eulertree

	#=====================
	def nullOrValue(self, val):
		if val is None:
			return 0
		else:
			return 1

	#=====================
	def calc3dRotationalDifference(self, eulerpair):
		e1 = { "euler1": eulerpair['part1']['euler1'], "euler2": eulerpair['part1']['euler2'], "euler3": eulerpair['part1']['euler3'] }
		e2 = { "euler1": eulerpair['part1']['euler1'], "euler2": eulerpair['part1']['euler2'], "euler3": eulerpair['part2']['euler3'] }
		rotdist = apEulerCalc.eulerCalculateDistanceSym(e1, e2, sym='d7', inplane=True)
		return rotdist

	#=====================
	def calc2dRotationalDifference(self, eulerpair):
		rotdist = abs(eulerpair['part1']['euler3'] - eulerpair['part2']['euler3']) % 360.0
		#DOES this number affect the total angle?
		if rotdist > 180.0:
			rotdist -= 360.0
		return rotdist

	#=====================
	def processEulers(self, eulertree):
		t0 = time.time()
		angdistlist = []
		totdistlist = []
		rotdistlist = []
		t0 = time.time()
		apDisplay.printMsg("Begin processing "+str(len(eulertree))+" euler distances")
		for eulerpair in eulertree:
			eulerpair['angdist'] = apEulerCalc.eulerCalculateDistanceSym(eulerpair['part1'],
				eulerpair['part2'], sym='d7', inplane=False)
			eulerpair['totdist'] = apEulerCalc.eulerCalculateDistanceSym(eulerpair['part1'],
				eulerpair['part2'], sym='d7', inplane=True)
			eulerpair['rotdist'] = self.calc2dRotationalDifference(eulerpair)
			if eulerpair['part1']['reject'] == 0 or eulerpair['part2']['reject'] == 0:
				angdistlist.append(eulerpair['angdist'])
				totdistlist.append(eulerpair['totdist'])
				rotdistlist.append(eulerpair['rotdist'])
		apDisplay.printMsg("Processed "+str(len(eulertree))+" eulers in "
			+apDisplay.timeString(time.time()-t0))

		self.writeRawDataFile(eulertree)
		self.writeKeepFiles(eulertree)
		self.writeScatterFile(eulertree)

		print "ANGLE EULER DATA:"
		#D-symmetry goes to 90, all other 180
		maxang = int(math.ceil(ndimage.maximum(angdistlist)))
		myrange = tuple((0,maxang,1))
		self.analyzeList(angdistlist, myrange, "angdata"+self.datastr+".dat")

		print "PLANE ROTATION DATA:"
		minrot = int(math.floor(ndimage.minimum(rotdistlist)))
		maxrot = int(math.ceil(ndimage.maximum(rotdistlist)))
		myrange = tuple((minrot,maxrot,1))
		self.analyzeList(rotdistlist, myrange, "rotdata"+self.datastr+".dat")

		print "TOTAL EULER DATA:"
		#D-symmetry goes to 90, all other 180
		maxtot = int(math.ceil(ndimage.maximum(totdistlist)))
		myrange = tuple((0,maxtot,1))
		self.analyzeList(totdistlist, myrange, "totaldata"+self.datastr+".dat")

		apDisplay.printMsg("Processed "+str(len(eulertree))+" eulers in "+apDisplay.timeString(time.time()-t0))

	#=====================
	def writeScatterFile(self, eulertree):
		"""
		write:
			(1) rotation angle diff in radians
			(2) tilt angle diff in degrees	
		for xmgrace display
		"""
		s = open("scatter"+self.datastr+".agr", "w")
		s.write("@g0 type Polar\n")
		s.write("@with g0\n")
		s.write("@    world 0, 0, "+str(round(2.0*math.pi,6))+", 60\n")
		s.write("@    xaxis  tick major "+str(round(2.0*math.pi/7.0,6))+"\n")
		s.write("@    xaxis  tick major grid on\n")
		s.write("@    xaxis  tick major linestyle 6\n")
		s.write("@    yaxis  tick major 15.0\n")
		s.write("@    yaxis  tick minor ticks 2\n")
		s.write("@    yaxis  tick major grid on\n")
		s.write("@    yaxis  tick minor grid on\n")
		s.write("@    yaxis  tick minor linewidth 0.5\n")
		s.write("@    yaxis  tick minor linestyle 4\n")
		s.write("@    frame linestyle 0\n")
		s.write("@    s0 symbol size 0.14\n")
		s.write("@    s0 line type 0\n")
		s.write("@    s0 symbol fill color 2\n")
		s.write("\n")
		s.write("@target G0.S0\n")
		for eulerpair in eulertree:
			mystr = ( "%3.8f %3.8f\n" % (eulerpair['rotdist']*math.pi/180.0, eulerpair['angdist']) )
			s.write(mystr)
		s.write("&\n")
		s.close()
		return

	#=====================
	def writeRawDataFile(self, eulertree):
		#write to file
		rawfile = "rawdata"+self.datastr+".dat"
		apDisplay.printMsg("Writing raw data to file: "+rawfile)
		r = open(rawfile, "w")
		r.write("p1-id\tp1-e1\tp1-e2\tp1-e3\tmirror\treject\t"
			+"p2-id\tp2-e1\tp2-e2\tp2-e3\tmirror\treject\t"
			+"ang-dist\trot-dist\ttotal-dist\n")
		for eulerpair in eulertree:
			mystr = ( 
				str(eulerpair['part1']['partid'])+"\t"+
				str(round(eulerpair['part1']['euler1'],2))+"\t"+
				str(round(eulerpair['part1']['euler2'],2))+"\t"+
				str(round(eulerpair['part1']['euler3'],2))+"\t"+
				str(eulerpair['part1']['mirror'])+"\t"+
				str(eulerpair['part1']['reject'])+"\t"+
				str(eulerpair['part2']['partid'])+"\t"+
				str(round(eulerpair['part2']['euler1'],2))+"\t"+
				str(round(eulerpair['part2']['euler2'],2))+"\t"+
				str(round(eulerpair['part2']['euler3'],2))+"\t"+
				str(eulerpair['part2']['mirror'])+"\t"+
				str(eulerpair['part2']['reject'])+"\t"+
				str(round(eulerpair['angdist'],2))+"\t"+
				str(round(eulerpair['rotdist'],2))+"\t"+
				str(round(eulerpair['totdist'],2))+"\n"
			)
			r.write(mystr)
		r.close()
		return

	#=====================
	def writeKeepFiles(self, eulertree):
		#find good particles
		totkeeplist = []
		angkeeplist = []
		for eulerpair in eulertree:
			if eulerpair['part1']['reject'] == 1 and eulerpair['part2']['reject'] == 1:
				continue
			if abs(eulerpair['totdist'] - 15.0) < 10.0:
				totkeeplist.append(eulerpair['part1']['partid']-1)
				totkeeplist.append(eulerpair['part2']['partid']-1)
			if abs(eulerpair['angdist'] - 15.0) < 10.0:
				angkeeplist.append(eulerpair['part1']['partid']-1)
				angkeeplist.append(eulerpair['part2']['partid']-1)
		#sort
		totkeeplist.sort()
		angkeeplist.sort()

		#write to file
		k = open("totkeepfile"+self.datastr+".lst", "w")
		for kid in totkeeplist:
			k.write(str(kid)+"\n")
		k.close()

		#write to file
		k = open("angkeeplist"+self.datastr+".lst", "w")
		for kid in angkeeplist:
			k.write(str(kid)+"\n")
		k.close()

		percent = "%3.1f" % (50.0*len(totkeeplist) / float(len(eulertree)))
		apDisplay.printMsg("Total Keeping "+str(len(totkeeplist))+" of "+str(2*len(eulertree))+" ("+percent+"%) eulers")
		percent = "%3.1f" % (50.0*len(angkeeplist) / float(len(eulertree)))
		apDisplay.printMsg("Angle Keeping "+str(len(angkeeplist))+" of "+str(2*len(eulertree))+" ("+percent+"%) eulers")
		return

	#=====================
	def analyzeList(self, mylist, myrange=(0,1,1), filename=None):
		"""
		histogram2(a, bins) -- Compute histogram of a using divisions in bins

		Description:
		   Count the number of times values from array a fall into
		   numerical ranges defined by bins.  Range x is given by
		   bins[x] <= range_x < bins[x+1] where x =0,N and N is the
		   length of the bins array.  The last range is given by
		   bins[N] <= range_N < infinity.  Values less than bins[0] are
		   not included in the histogram.
		Arguments:
		   a -- 1D array.  The array of values to be divied into bins
		   bins -- 1D array.  Defines the ranges of values to use during
		         histogramming.
		Returns:
		   1D array.  Each value represents the occurences for a given
		   bin (range) of values.
		"""
		#hist,bmin,minw,err = stats.histogram(mynumpy, numbins=36)
		#print hist,bmin,minw,err,"\n"
		mymin = float(myrange[0])
		mymax = float(myrange[1])
		mystep = float(myrange[2])

		mynumpy = numpy.asarray(mylist, dtype=numpy.float32)
		print "range=",round(ndimage.minimum(mynumpy),2)," <> ",round(ndimage.maximum(mynumpy),2)
		print " mean=",round(ndimage.mean(mynumpy),2)," +- ",round(ndimage.standard_deviation(mynumpy),2)
		
		#histogram
		bins = []
		mybin = mymin
		while mybin <= mymax:
			bins.append(mybin)
			mybin += mystep
		bins = numpy.asarray(bins, dtype=numpy.float32)
		apDisplay.printMsg("Creating histogram with "+str(len(bins))+" bins")
		hist = stats.histogram2(mynumpy, bins=bins)
		#print bins
		#print hist
		if filename is not None:
			f = open(filename, "w")
			for i in range(len(bins)):
				out = ("%3.4f %d\n" % (bins[i] + 2.5, hist[i]) )
				f.write(out)
			f.write("&\n")

	def subStackCmd(self):
		keepfile = os.path.join(self.params['outdir'], "angkeepfile"+self.datastr+".lst")
		stackdata = apStack.getRunsInStack(self.params['stackid'])

		cmd = ( "subStack.py "
			+" --old-stack-id="+str(self.params['stackid'])
			+" \\\n"+" --keep-file="+keepfile
			+" \\\n"+" --new-stack-name=sub-"+stackdata[0]['stackRun']['stackRunName']
			+" --commit"
			+" --description='xxx xx' \n" )
		print "New subStack.py Command:"
		apDisplay.printColor(cmd, "purple")

	######################################################
	####  ITEMS BELOW WERE SPECIFIED BY AppionScript  ####
	######################################################

	#=====================
	def onInit(self):
		self.datastr = "_r"+str(self.params['reconid'])+"_i"+str(self.params['iternum'])

	#=====================
	def setProcessingDirName(self):
		self.processdirname = os.path.join(self.functionname, "sat-recon"+str(self.params['reconid']))

	#=====================
	def setupParserOptions(self):
		self.parser.set_usage("Usage: %prog --reconid=<##> --commit [options]")
		self.parser.add_option("-r", "--reconid", dest="reconid", type='int',
			help="Reconstruction Run ID", metavar="INT")
		self.parser.add_option("-i", "--iternum", dest="iternum", type='int',
			help="Reconstruction Iteration Number, defaults to last iteration", metavar="INT")
		self.parser.add_option("-o", "--outdir", dest="outdir",
			help="Location to copy the templates to", metavar="PATH")
		self.parser.add_option("--tiltrunid", dest="tiltrunid", type='int',
			help="Automatically set", metavar="INT")
		self.parser.add_option("--stackid", dest="stackid", type='int',
			help="Automatically set", metavar="INT")
		self.parser.add_option("-C", "--commit", dest="commit", default=False,
			action="store_true", help="Commit template to database")
		self.parser.add_option("--no-commit", dest="commit", default=False,
			action="store_false", help="Do not commit template to database")

	#=====================
	def checkConflicts(self):
		"""
		make sure the necessary parameters are set correctly
		"""
		if not self.params['reconid']:
			apDisplay.printError("Enter a Reconstruction Run ID, e.g. --reconid=243")
		if not self.params['tiltrunid']:
			self.params['tiltrunid'] = self.getTiltRunIDFromReconID(self.params['reconid'])
		if not self.params['iternum']:
			self.params['iternum'] = self.getLastIterationFromReconID(self.params['reconid'])
		if not self.params['stackid']:
			self.params['stackid'] = apStack.getStackIdFromRecon(self.params['reconid'])

	#=====================
	def start(self):
		#reconid = 186, 194, 239, 243
		#tiltrunid = 557, 655
		### Big slow process
		if self.params['commit'] is True:
			t0 = time.time()
			results = self.getEulersForIteration(self.params['reconid'], self.params['tiltrunid'], self.params['iternum'])
			eulertree = self.convertSQLtoEulerTree(results)
			self.processEulers(eulertree)
			apDisplay.printMsg("Total time for "+str(len(eulertree))+" eulers: "+apDisplay.timeString(time.time()-t0))
		else:
			apDisplay.printWarning("Not committing results")
		self.subStackCmd()

#=====================
if __name__ == "__main__":
	satEuler = satEulerScript()
	satEuler.start()
	satEuler.close()







