#!/usr/bin/env python

import timedloop
import event
import time
#import Numeric
import base64
import array
import copy

class AcquireLoop(timedloop.TimedLoop):
	"""
	A node that implements a timed image acquisition loop.
	The default interval is 0 seconds, meaning it will acquire
	images as fast as possible.
	Event Inputs:
		StartEvent - starts the acquisition loop
		StopEvent - stops the acquisition loop
		NumericControlEvent - modifies the loop interval
	"""
	def __init__(self, nodeid, managerlocation):
		timedloop.TimedLoop.__init__(self, nodeid, managerlocation)
		self.addEventOutput(event.PublishEvent)

	def action(self):
		"""
		this is the real guts of this node
		"""

		# this is rough, ImageData type, etc. to come soon
		camerastate = self.researchByDataID('camera')
		imagearray = array.array(camerastate.content['datatype code'], base64.decodestring(camerastate.content['image data']))
		print 'image 1...10', imagearray[:10]

		c = copy.copy(camerastate.content)
		del c['image data']
		print c

		## acquire image
		print 'acquiring image %s' % time.asctime()

		## publish image
		self.publish(camerastate, event.PublishEvent)

