#!/usr/bin/env python
from pyscope import jeolcom

class StandardValues(object):
	def __init__(self):
		self.tem = jeolcom.Jeol()
		self.tem.findMagnifications()
		self.lensnames = {'MAG1':'OL','LOWMAG':'OM'}
		if self.tem.getJeolConfig('tem option','use_pla'):
			self.imageshift_class = getattr(self.tem.def3,'GetPLA')
		else:
			self.imageshift_class = getattr(self.tem.def3,'GetIS1')
		self.configs = {}

	def addConfig(self,option,item):
		if option not in self.configs.keys():
			self.configs[option] = []
		self.configs[option].append(item)

	def displayConfig(self):
		for option in self.configs.keys():
			print option
			for item in self.configs[option]:
				print item
			print ''

	def getStandardFocus(self, mag):
		submode = self.tem.getProjectionSubModeName()
		lensname = self.lensnames[submode.upper()]
		focus_class = getattr(self.tem,'getRawFocus%s' % (lensname))
		option = '[%s standard focus]' % lensname.lower()
		item = '%d:%d' % (mag,focus_class())
		self.addConfig(option,item)

	def getNeutralShift(self, mag, shiftname, shift_class):
		shift = shift_class()
		option = '[neutral %s]' % (shiftname.lower())
		item = '%d:%d,%d' % (mag,shift[0],shift[1])
		self.addConfig(option,item)

	def run(self):
		print 'Change to a magnification manually so that standard focus and neutral values are set'
		t = raw_input('hit return key to start')
		while not t:
			mag = self.tem.getMagnification()
			self.getStandardFocus(mag)
			self.getNeutralShift(mag,'imageshift',self.imageshift_class)
			self.getNeutralShift(mag,'Beamshift',self.tem.def3.GetCLA1)
			self.getNeutralShift(mag,'Beamtilt',self.tem.def3.GetCLA2)
			t = raw_input('Change to a new mag and then hit return key to start\nOtherwise hit other keys to display the summary')
		self.displayConfig()
		print ''
		raw_input('hit any key to end')

if __name__=='__main__':
	app = StandardValues()
	app.run()
