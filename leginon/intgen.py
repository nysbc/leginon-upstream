#!/usr/bin/env python

import node, event
import time
import data

class IntGen(node.Node):
	def __init__(self, nodeid, managerlocation):
		node.Node.__init__(self, nodeid, managerlocation)

		self.addEventOutput(event.NumericControlEvent)
		self.addEventOutput(event.StartEvent)
		self.addEventOutput(event.StopEvent)

		print self.location()
		print self.nodeid

		self.main()

	def sendint(self, newint):
		self.announce(event.NumericControlEvent(newint))

	def sendstart(self):
		self.announce(event.StartEvent())

	def sendstop(self):
		self.announce(event.StopEvent())
			
	def main(self):
		self.interact()

if __name__ == '__main__':
	import signal, sys

	manloc = {}
	manloc['hostname'] = sys.argv[1]
	manloc['TCP port'] = int(sys.argv[2])

	m = IntGen(manloc)
	try:
		signal.pause()
	except KeyboardInterrupt:
		sys.exit()
