#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#
import camera
import sys

if sys.platform != 'win32':
	class gatan(camera.Camera):
		def __init__(self):
			pass
else:
	sys.coinit_flags = 0
	import pythoncom
	import win32com.client
	import gatancom

	class Gatan(camera.Camera):
		def __init__(self):
			pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
			self.theCamera = win32com.client.Dispatch("TecnaiCCD.GatanCamera")        
	    
		def __del__(self):
			pass

		def getImage(self, offset, dimension, binning, exposure_time, imagetype):
			if binning['x'] != binning['y']:
				raise ValueError
			self.theCamera.CameraLeft = offset['x']
			self.theCamera.CameraRight = offset['x'] + dimension['x']
			self.theCamera.CameraTop = offset['y']
			self.theCamera.CameraBottom = offset['y'] + dimension['y']
			self.theCamera.Binning = binning['x']
			self.theCamera.ExposureTime = float(exposure_time) / 1000.0
	
			return self.theCamera.AcquireRawImage()

		def insert(self):
			self.theCamera.Insert()

		def retract(self):
			self.theCamera.Retract()

		def setInserted(self, value):
			if value:
				self.insert()
			else:
				self.retract()

		def getInserted(self):
			if self.theCamera.IsInserted == 1:
				return True
			else:
				return False

