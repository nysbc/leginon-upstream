#!/usr/bin/env python

import scipy.fftpack
import scipy.__config__
if not scipy.__config__.get_info('fftw3_info'):
	raise ImportError

def real_fft2d(*args, **kwargs):
	return scipy.fftpack.fft2(*args, **kwargs)

def inverse_real_fft2d(*args, **kwargs):
	return scipy.fftpack.ifft2(*args, **kwargs).real

import time

class _fftEngine(object):
	'''base class for a FFT engine'''
	def __init__(self, *args, **kwargs):
		self.showtime = 0

	def transform(self, image):
		transimage = self.timer(self._transform, (image,))
		return transimage

	def itransform(self, image):
		itransimage = self.timer(self._itransform, (image,))
		return itransimage

	def timer(self, func, args=()):
		t0 = time.time()
		ret = apply(func, args)
		t1 = time.time()
		total = t1 - t0
		if self.showtime:
			print '%s %.5f' % (func.__name__, total)

		return ret

	def _transform(self, image):
		raise NotImplementedError()

	def _itransform(self, image):
		raise NotImplementedError()


### this attempts to use fftw single and double
### if that fails, it will use scipy
fftw_mods = []

try:
	import fftw.single
	fftw_mods.append(fftw.single)
	import fftw.double
	fftw_mods.append(fftw.double)
except ImportError:
	pass
	#print 'could not import fftw modules'


class fftEngine(_fftEngine):
	'''subclass of fftEngine which uses FFT from scipy module'''
	def __init__(self, *args, **kwargs):
		_fftEngine.__init__(self)

	def _transform(self, im):
		fftim = real_fft2d(im)
		return fftim

	def _itransform(self, fftim):
		im = inverse_real_fft2d(fftim)
		return im

if __name__ == '__main__':
	import Mrc
	import imagefun

	def stats(im):
		print '   MEAN', imagefun.mean(im)
		print '   STD', imagefun.stdev(im)
		print '   MIN', imagefun.min(im)
		print '   MAX', imagefun.max(im)

	print 'reading'
	im = Mrc.mrc_to_numeric('../test_images/spiketest.mrc')
	print 'IM TYPE', im.type()
	stats(im)
	ffteng = fftEngine()
	fft = ffteng.transform(im)
	print 'FFT TYPE', fft.type()
	ifft = ffteng.itransform(fft)
	print 'IFFT TYPE', ifft.type()
	stats(ifft)
