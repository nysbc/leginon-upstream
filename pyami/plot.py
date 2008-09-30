#!/usr/bin/env python

import pylab

def plot(*args, **kwargs):
	pylab.plot(*args, **kwargs)
	pylab.show()

if __name__ == '__main__':
	import mrc
	import sys
	import numextension
	import imagefun
	import numpil
	a = mrc.read(sys.argv[1])
	low = float(sys.argv[2])
	high = float(sys.argv[3])

	print 'SHAPE', a.shape
	#pow = imagefun.power(a)
	#numpil.write(pow, 'pow.png')
	b = numextension.radialPower(a, low, high)
	plot(b)
	raw_input('enter to quit')
