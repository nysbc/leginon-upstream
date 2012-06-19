#!/usr/bin/env python

import time
import math
import numpy
from appionlib import apDisplay
from appionlib.apCtf import ctftools

debug = False

#===================
def generateCTF1d(radii=None, numpoints=256, focus=1.0e-6, 
	pixelsize=1.5e-10, cs=2e-3, volts=120000, ampconst=0.07):
	"""
	calculates a CTF function based on the input details

	Use SI units: meters, radians, volts
	Underfocus is postive (defocused) 
	"""
	if debug is True:
		print "generateCTF1d()"
	t0 = time.time()
	checkParams(focus1=focus, focus2=focus, pixelsize=pixelsize, cs=cs, 
		volts=volts, ampconst=ampconst)
	minres = 1e10/radii.min()
	maxres = 1e10/radii.max()
	if debug is True:
		print "** CTF limits %.1f A -->> %.1fA"%(minres, maxres)
	if maxres < 2.0 or maxres > 50.0:
		apDisplay.printError("CTF limits are incorrect %.1f A -->> %.1fA"%(minres, maxres))

	if radii is None:
		radii = generateRadii1d(numpoints, pixelsize)
	else:
		numpoints = len(radii)

	wavelength = ctftools.getTEMLambda(volts)

	ctf = numpy.zeros((numpoints), dtype=numpy.float64)

	x4 = math.pi/2.0 * wavelength**3 * cs
	x2 = math.pi * wavelength
	x0 = -1.0*math.asin(ampconst) #CORRECT
	#x0 = 1.0*math.asin(ampconst)   #MAYBE CORRECT
	if debug is True:
		print "x0 shift %.1f degrees"%(math.degrees(x0))

	radiisq = radii**2

	gamma = (x4 * radiisq**2) + (-focus * x2 * radiisq) + (x0)
	#ctf = -1.0*numpy.cos(gamma) #WRONG
	#ctf = -1.0*numpy.sin(gamma) #CORRECT
	ctf = 1.0*numpy.sin(gamma) #MAYBE CORRECT

	if debug is True:
		print "generate 1D ctf complete in %.4f sec"%(time.time()-t0)

	return ctf

#===================
def generateRadii1d(numpoints=256, pixelsize=1e-10):
	radfreq = 1.0/( numpoints*pixelsize )
	radii = numpy.arange(numpoints) * radfreq
	return radii

#===================
def generateCTF2d(focus1=-1.0e-6, focus2=-1.0e-6, theta=0.0, 
	shape=(256,256), pixelsize=1.0e-10, cs=2e-3, volts=120000, ampconst=0.000):
	"""
	calculates a CTF function based on the input details

	Use SI units: meters, radians, volts
	Underfocus is postive (defocused) 
	"""
	t0 = time.time()

	wavelength = getTEMLambda(volts)

	xfreq = 1.0/( (shape[1]-1)*2.*pixelsize )
	yfreq = 1.0/( (shape[0]-1)*2.*pixelsize )

	ctf = numpy.zeros(shape, dtype=numpy.float64)

	meanfocus = (focus1 + focus2) / 2.
	focusdiff = (focus1 - focus2) / 2. 

	t1 = math.pi * wavelength
	t2 = wavelength**2 * cs / 2.0
	t3 = -1.0*math.asin(ampconst)

	radiisq = circle.generateRadial1d(shape, xfreq, yfreq)
	angles = -circle.generateAngular2d(shape, xfreq, yfreq)
	localfocus = meanfocus + focusdiff * numpy.cos(2.0*(angles-theta))
	gamma = t1*radiisq * (-localfocus + t2*radiisq) + t3
	ctf = numpy.sin(gamma)

	gauss = circle.generateGaussion2d(shape)
	imagefile.arrayToJpeg(gauss, "gauss2.jpg")

	if debug is True:
		print "generate ctf 2d complete in %.4f sec"%(time.time()-t0)

	return ctf*gauss

#===================
def generateAngular2d(shape, xfreq, yfreq):
	"""
	this method is about 2x faster than method 1
	"""
	t0 = time.time()
	if shape[0] % 2 != 0 or shape[1] % 2 != 0:
		apDisplay.printError("array shape for radial function must be even")

	halfshape = numpy.array(shape)/2.0
	a = Angular(halfshape, xfreq, yfreq, center=False, flip=False)
	angular1 = a.angular
	b = Angular(halfshape, xfreq, yfreq, center=False, flip=True)
	angular2 = numpy.fliplr(b.angular)
	circular = numpy.vstack( 
		(numpy.hstack( 
			(numpy.flipud(angular2), -numpy.flipud(angular1))
		),numpy.hstack( 
			(-angular2, angular1), 
		)))

	### raw radius from center
	#print numpy.around(circular*180/math.pi,1)
	print "angular 2 complete in %.4f sec"%(time.time()-t0)
	return circular

#===================
def generateGaussion2d(shape, sigma=None):
	"""
	this method is about 4x faster than method 1
	"""
	t0 = time.time()
	if sigma is None:
		sigma = numpy.mean(shape)/4.0
	circular = generateRadial2(shape)
	circular = numpy.exp(-circular/sigma**2)
	print "gaussian 2 complete in %.4f sec"%(time.time()-t0)
	return circular

#===================
class Radial(object):
	def __init__(self, shape, xfreq=1.0, yfreq=1.0, center=True):
		# setup
		if center is True:
			### distance from center
			self.center = numpy.array(shape, dtype=numpy.float64)/2.0 - 0.5
		else:
			### the upper-left edge
			self.center = (-0.5, -0.5)
		self.xfreqsq = xfreq**2
		self.yfreqsq = yfreq**2
		# function
		self.radial = numpy.fromfunction(self.distance, shape, dtype=numpy.float64)

	def distance(self, y, x):
		distance = (
			(x - self.center[1])**2 * self.xfreqsq 
			+ (y - self.center[0])**2 * self.yfreqsq
		)
		return distance

#===================
def generateRadial2d(shape, xfreq, yfreq):
	"""
	this method is about 4x faster than method 1
	"""
	t0 = time.time()
	if shape[0] % 2 != 0 or shape[1] % 2 != 0:
		apDisplay.printError("array shape for radial function must be even")

	halfshape = numpy.array(shape)/2.0
	#radial = numpy.fromfunction(radiusfunc, halfshape)
	r = Radial(halfshape, xfreq, yfreq, center=False)
	radial = r.radial
	circular = numpy.vstack( 
		(numpy.hstack( 
			(numpy.fliplr(numpy.flipud(radial)), numpy.flipud(radial))
		),numpy.hstack( 
			(numpy.fliplr(radial), radial), 
		)))
	### raw radius from center
	#print circular
	print "radial 2 complete in %.4f sec"%(time.time()-t0)
	return circular

#===================
def checkParams(focus1=-1.0e-6, focus2=-1.0e-6, pixelsize=1.5e-10, 
	cs=2e-3, volts=120000, ampconst=0.07):
	if debug is True:
		print "  Defocus1 %.2f microns (underfocus is positive)"%(focus1*1e6)
		if focus1 != focus2:
			print "  Defocus2 %.2f microns (underfocus is positive)"%(focus2*1e6)
		print "  Pixelsize %.3f Angstroms"%(pixelsize*1e10)
		print "  C_s %.1f mm"%(cs*1e3)
		print "  High tension %.1f kV"%(volts*1e-3)
		print ("  Amp Contrast %.3f (shift %.1f degrees)"
			%(ampconst, math.degrees(-math.asin(ampconst))))
	if focus1*1e6 > 10.0 or focus1*1e6 < 0.1:
		apDisplay.printError("atypical defocus #1 value %.1f microns (underfocus is positve)"
			%(focus1*1e6))
	if focus2*1e6 > 10.0 or focus2*1e6 < 0.1:
		apDisplay.printError("atypical defocus #2 value %.1f microns (underfocus is positve)"
			%(focus2*1e6))
	if cs*1e3 > 4.0 or cs*1e3 < 0.4:
		apDisplay.printError("atypical C_s value %.1f mm"%(cs*1e3))
	if pixelsize*1e10 > 20.0 or pixelsize*1e10 < 0.1:
		apDisplay.printError("atypical pixel size value %.1f Angstroms"%(pixelsize*1e10))
	if volts*1e-3 > 400.0 or volts*1e-3 < 60:
		apDisplay.printError("atypical high tension value %.1f kiloVolts"%(volts*1e-3))
	if ampconst < 0.0 or ampconst > 0.4:
		apDisplay.printError("atypical amplitude contrast value %.3f"%(ampconst))
	return

#===================
#===================
#===================
if __name__ == "__main__":
	r = generateRadial2d((8,8), 0.1, 0.1)
	radii = generateRadii1d()
	ctf = generateCTF1d(radii)
	from matplotlib import pyplot
	pyplot.plot(radii, ctf, 'r-', )
	pyplot.show()


