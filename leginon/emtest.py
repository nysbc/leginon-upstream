#!/usr/bin/env python

import node, event
import time
import data

class EMTest(node.Node):
	def __init__(self, id, managerlocation):
		node.Node.__init__(self, id, managerlocation)

		#self.addEventInput(event.ControlEvent, self.handle_intervalchange)
		#self.addEventInput(event.PublishEvent, self.handle_intervalpublished)
		#self.addEventOutput(event.PublishEvent)

		print "starting emtest..."
		magdata = self.researchByDataID('magnification')
		print magdata.content

		magdata.content['magnification'] = 10
		self.publishRemote(magdata.origin['location'], magdata)

		newmagdata = self.researchByDataID('magnification')
		print newmagdata.content

if __name__ == '__main__':
	pass

