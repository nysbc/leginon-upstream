#!/usr/bin/env python

import sys
import time
import math
import numpy
import random
from pyami import ellipse
from scipy.ndimage import filters
from appionlib.apCtf import ctftools
from matplotlib import pyplot

#=========================
def trimZeroEdges(oldarray):
	"""
	takes a 2D array an cuts out the center
	that is removes zero filled edges

	this should help speed up the ellipse RANSAC search
	"""
	columnvals = oldarray.sum(0)
	rowvals = oldarray.sum(0)
	## reverse and add
	columnvals = columnvals + columnvals[::-1]
	rowvals = rowvals + rowvals[::-1]
	## find first non-zero value
	firstColumnValue = numpy.nonzero(rowvals)[0][0]
	firstRowValue = numpy.nonzero(rowvals)[0][0]
	cutsize = min(firstColumnValue,firstRowValue)-4
	newshape = numpy.array(oldarray.shape, dtype=numpy.uint16) - 2*cutsize
	#print "resize", oldarray.shape, newshape
	cutarray = frame_cut(oldarray, newshape)
	return cutarray


#=================
def printParams(params):
	a = params['a']
	b = params['b']
	alpha = params['alpha']
	print ("ellip: %d x %d < %.1f deg"%
		(a, b, alpha*180/math.pi))
	return

#=========================
def frame_cut(a, newshape):
	"""
	clips image, similar to EMAN1's proc2d clip=X,Y
	
	>>> a = num.arange(16, shape=(4,4))
	>>> frame_cut(a, (2,2))
	array(
			[[5,  6],
		   [9, 10]])
	"""
	mindimx = int( (a.shape[0] / 2.0) - (newshape[0] / 2.0) )
	maxdimx = int( (a.shape[0] / 2.0) + (newshape[0] / 2.0) )
	mindimy = int( (a.shape[1] / 2.0) - (newshape[1] / 2.0) )
	maxdimy = int( (a.shape[1] / 2.0) + (newshape[1] / 2.0) )
	return a[mindimx:maxdimx, mindimy:maxdimy]

#=========================
def ellipseRANSAC(edgeMap, ellipseThresh=2, minPercentGoodPoints=0.001, certainProb=0.9, maxiter=5000):
	"""
	takes 2D edge map from image and trys to find a good ellipse in the data
	"""
	shrinkEdgeMap = numpy.float64(trimZeroEdges(edgeMap))
	#shrinkEdgeMap = numpy.float64(edgeMap)
	shape = shrinkEdgeMap.shape

	## make a list of edges, with x, y radii
	bottomEdgeMap = numpy.copy(shrinkEdgeMap)
	bottomEdgeMap[:shape[0]/2,:] = 0
	topEdgeMap = numpy.copy(shrinkEdgeMap)
	topEdgeMap[shape[0]/2:,:] = 0
	rightEdgeMap = numpy.copy(shrinkEdgeMap)
	rightEdgeMap[:,:shape[1]/2] = 0
	leftEdgeMap = numpy.copy(shrinkEdgeMap)
	leftEdgeMap[:,shape[1]/2:] = 0

	#sort edges into quadrants and choose that way
	center = numpy.array(shape, dtype=numpy.float64)/2.0 - 0.5
	edgeList = numpy.array(numpy.where(shrinkEdgeMap), dtype=numpy.float64).transpose() - center
	bottomEdgeList = numpy.array(numpy.where(bottomEdgeMap), dtype=numpy.float64).transpose() - center
	topEdgeList = numpy.array(numpy.where(topEdgeMap), dtype=numpy.float64).transpose() - center
	rightEdgeList = numpy.array(numpy.where(rightEdgeMap), dtype=numpy.float64).transpose() - center
	leftEdgeList = numpy.array(numpy.where(leftEdgeMap), dtype=numpy.float64).transpose() - center

	numEdges = shrinkEdgeMap.sum()
	if numEdges != len(edgeList):
		print "something weird in array sizes"
		return None

	numSamples = 4

	## count rejects
	areaReject = 0
	distReject = 0
	ratioReject = 0
	sizeReject = 0
	validEllipse = 0

	## reject criteria
	maxDistFromCenter = math.hypot(shape[0], shape[1])/10.0
	squareArea = max(edgeMap.shape)**2/4 #quarter of the image, little less than indcribed circle
	maxShrinkRadius = int(max(shape)*0.7) #to the corner of shrink image
	maxNormRadius = max(edgeMap.shape)/2 #to the side of full image
	maxRadius = min(maxShrinkRadius, maxNormRadius)
	minGoodPoints = minPercentGoodPoints*numEdges
	finalMinEdges = numEdges*(1.0 - math.exp( math.log(1.0-certainProb)/maxiter ) )**(1.0/numSamples)

	mostGoodPoints = 0
	bestEllipseParams = None # {'center':(x,y), 'a':a, 'b':b, 'alpha':radians}
	iternum = 0
	t0 = time.time()
	while iternum <= maxiter:
		iternum += 1

		currentProb = 1.0 - math.exp( math.log(1.0-certainProb)/iternum )
		currentProb = currentProb**(1.0/numSamples)

		if iternum % 500 == 0:
			print ("RANSAC iter=%d/%d, points=%d, need=%d->%d, bestProb=%.1f, timePer=%.4f"
				%(iternum, maxiter, mostGoodPoints, currentProb*numEdges, 
					finalMinEdges, mostGoodPoints/float(numEdges)*100, 
					(time.time()-t0)/float(iternum)))

		## check to see if we can stop
		if mostGoodPoints > currentProb*numEdges:
			currentProb = mostGoodPoints/float(numEdges)
			successProb = 1.0 - math.exp( iternum * math.log(1.0 - currentProb**numSamples) )
			print "\nRANSAC SUCCESS"
			break

		if currentProb < minPercentGoodPoints:
			print "\nRANSAC FAILURE"
			break

		if iternum >= maxiter:
			print "\nRANSAC GAVE UP"
			break

		#choose random edges
		#might be better to sort edges into quadrants and choose that way
		currentEdges = []
		currentEdges.append(random.choice(bottomEdgeList))
		currentEdges.append(random.choice(topEdgeList))
		currentEdges.append(random.choice(leftEdgeList))
		currentEdges.append(random.choice(rightEdgeList))
		currentEdges = numpy.array(currentEdges, dtype=numpy.int16)

		# solve centered ellipse, fixed center
		centeredParams = ellipse.solveEllipseOLS(currentEdges)
		#print centeredParams
		if centeredParams is None:
			#sys.stderr.write("c")
			continue
		## check to see if ellipse has a area smaller than circle inscribed in image
		area = centeredParams['a'] * centeredParams['b']
		if area > squareArea:
			areaReject += 1
			#sys.stderr.write("A%d "%(areaReject))
			continue
		radius = max(centeredParams['a'],centeredParams['b'])
		if radius > maxRadius:
			sizeReject += 1
			#sys.stderr.write("S%d "%(sizeReject))
			continue	
		ratio = centeredParams['a']/float(centeredParams['b'])
		if ratio > 4 or ratio < 0.25:
			ratioReject += 1
			#sys.stderr.write("R%d "%(ratioReject))
			continue	

		## check to see if ellipse has a circumference smaller than something

		# solve general ellipse, floating center
		## only a few points, can use solveEllipseGander fit
		#generalParams = ellipse.solveEllipseB2AC(currentEdges)
		generalParams = ellipse.solveEllipseGander(currentEdges)
		if generalParams is not None:
			## check center to see if its reasonably close to center
			distFromCenter = math.hypot(generalParams['center'][0], generalParams['center'][1])
			if distFromCenter > maxDistFromCenter:
				distReject += 1
				#sys.stderr.write("D%d "%(distReject))
				continue
			## check to see if ellipse has a area smaller than circle inscribed in image
			area = math.pi * centeredParams['a'] * centeredParams['b']
			if area > squareArea:
				areaReject += 1
				#sys.stderr.write("a%d "%(areaReject))
				continue
			radius = max(centeredParams['a'],centeredParams['b'])
			if radius > maxRadius:
				sizeReject += 1
				#sys.stderr.write("s%d "%(sizeReject))
				continue	
			ratio = centeredParams['a']/float(centeredParams['b'])
			if ratio > 6 or ratio < 0.16:
				ratioReject += 1
				#sys.stderr.write("r%d "%(ratioReject))
				continue	

		## create an outline of the ellipse
		ellipseMap = generateEllipseRangeMap2(centeredParams, ellipseThresh, shape)

		## take overlap of edges and fit area to determine number of good points
		goodPoints = (shrinkEdgeMap*ellipseMap).sum()

		#if goodPoints > mostGoodPoints or iternum%100 == 0:
		#	print ("\ngood points=%d (best=%d; need=%d->%d, bestProb=%.1f, iter=%d/%d, timePer=%.4f)"
		#		%(goodPoints, mostGoodPoints, currentProb*numEdges, finalMinEdges,
		#			mostGoodPoints/float(numEdges)*100, iternum, maxiter, 
		#			(time.time()-t0)/float(iternum)))

		validEllipse += 1

		if goodPoints < minGoodPoints or goodPoints < mostGoodPoints:
			#sys.stderr.write(".")
			continue

		if goodPoints > mostGoodPoints:
			### refine the ellipse parameters to see if we can do better
			centeredEllipseMap1 = generateEllipseRangeMap2(centeredParams, ellipseThresh, shape)
			centeredEllipseList1 = numpy.array(numpy.where(centeredEllipseMap1), dtype=numpy.float64).transpose() - center
			betterEllipseParams1 = ellipse.solveEllipseOLS(centeredEllipseList1)
			betterEllipseMap1 = generateEllipseRangeMap2(betterEllipseParams1, ellipseThresh, shape)
			betterGoodPoints1 = (shrinkEdgeMap*betterEllipseMap1).sum()
			centeredEllipseMap2 = generateEllipseRangeMap2(centeredParams, ellipseThresh*8, shape)
			centeredEllipseList2 = numpy.array(numpy.where(centeredEllipseMap2), dtype=numpy.float64).transpose() - center
			betterEllipseParams2 = ellipse.solveEllipseOLS(centeredEllipseList2)
			betterEllipseMap2 = generateEllipseRangeMap2(betterEllipseParams2, ellipseThresh, shape)
			betterGoodPoints2 = (shrinkEdgeMap*betterEllipseMap2).sum()
			#print goodPoints, betterGoodPoints1, betterGoodPoints2

			if betterGoodPoints1 > goodPoints and betterGoodPoints1 > betterGoodPoints2:
				bestEllipseParams = betterEllipseParams1
				mostGoodPoints = betterGoodPoints1
			elif betterGoodPoints2 > goodPoints:
				bestEllipseParams = betterEllipseParams2
				mostGoodPoints = betterGoodPoints2
			else:
				bestEllipseParams = centeredParams
				mostGoodPoints = goodPoints

			printParams(bestEllipseParams)

	### end loop and do stuff
	#bestEllipseMap = generateEllipseRangeMap2(bestEllipseParams, ellipseThresh*1.5, edgeMap.shape)
	#bestEllipseList = numpy.array(numpy.where(bestEllipseMap), dtype=numpy.float64).transpose() - center
	#betterEllipseParams = ellipse.solveEllipseOLS(bestEllipseList)

	print "total iterations", iternum
	print "\tpercent good points %.1f"%(mostGoodPoints/float(numEdges)*100)
	print "\ttime per iter %.2f ms"%(1000.*(time.time()-t0)/float(iternum))
	print "\tvalid ellipses", validEllipse
	print "\toff-center rejects", distReject
	print "\tlarge area rejects", areaReject
	print "\tlarge radius rejects", sizeReject
	print "\toblong ratio rejects", ratioReject
	printParams(bestEllipseParams)


	return bestEllipseParams


#=================
def generateEllipseRangeMap2(ellipseParams, ellipseThresh, shape):
	'''
	make an elliptical ring of width 1 based on ellipseParams
	'''
	a = ellipseParams['a']
	b = ellipseParams['b']
	## this should be negative because we are using negative convention in viewer
	alpha = -ellipseParams['alpha']

	maxradius = max(a,b)
	numpoints = int(math.ceil(6.28*maxradius))

	ellipseRange = numpy.zeros(shape, dtype=numpy.float64)

	center = numpy.array(shape, dtype=numpy.float64)/2.0
	points = ellipse.generate_ellipse(a, b, alpha, center=center, numpoints=numpoints, integers=True)

	#remove negative coordinates, off screen
	if points.min() < 0:
		mins = points.min(1)
		abovezero = numpy.where(mins > 0)
		points = points[abovezero]

	#remove too large coordinates, off screen
	if points.max() > min(shape)-1:
		maxs = points.max(1)
		belowedge = numpy.where(maxs < min(shape)-1)
		points = points[belowedge]

	ellipseRange[points[:,0],points[:,1]] = 1.0
	ellipseRange = filters.maximum_filter(ellipseRange, size=ellipseThresh)
	ellipseRange2 = filters.maximum_filter(ellipseRange, size=ellipseThresh*2)
	ellipseRange = ellipseRange + ellipseRange2*0.1

	return ellipseRange

#=================
def generateEllipseRangeMap(ellipseParams, ellipseThresh, shape):
	"""
	make an elliptical ring of width ellipseThresh based on ellipseParams
	"""
	raise DeprecationWarning
	largeEllipse = drawFilledEllipse(shape, ellipseParams['a']+ellipseThresh, 
		ellipseParams['b']+ellipseThresh, ellipseParams['alpha'])
	smallEllipse = drawFilledEllipse(shape, ellipseParams['a']-ellipseThresh, 
		ellipseParams['b']-ellipseThresh, ellipseParams['alpha'])
	ellipseRange = numpy.logical_and(largeEllipse, -smallEllipse)
	return ellipseRange

#=================
def drawFilledEllipse(shape, a, b, alpha):
	'''
	Generate a zero initialized image array with a filled ellipse
	drawn by setting pixels to 1.

	see also imagefun.filled_circle
	'''
	raise DeprecationWarning
	ellipratio = a/float(b)
	### this step is TOO SLOW
	radial = ctftools.getEllipticalDistanceArray(ellipratio, -math.degrees(alpha), shape)
	meanradius = math.sqrt(a*b)
	filledEllipse = numpy.where(radial > meanradius, False, True)
	return filledEllipse

#=================
#=================
if __name__ == "__main__":
	from scipy.misc import lena
	from matplotlib import pyplot
	from appionlib.apCtf import canny
	lena = lena()

	edgeMap = canny.canny_edges(lena, 5, 0.25, 0.75)
	edgeMapInv = numpy.flipud(numpy.fliplr(edgeMap))
	edgeMap = numpy.logical_or(edgeMap,edgeMapInv)

	thresh = 3

	t0 = time.time()
	ellipseParams = ellipseRANSAC(edgeMap)
	print time.time()-t0, "seconds"

	if ellipseParams is None:
		raise

	filled1 = generateEllipseRangeMap2(ellipseParams, thresh, edgeMap.shape)
	filled2 = generateEllipseRangeMap2(ellipseParams, thresh*3, edgeMap.shape)
	filled = edgeMap + filled2 - filled1
	pyplot.imshow(filled)
	pyplot.gray()
	pyplot.show()




