#!/usr/bin/env python
import os
import sys
import sinedon
from pyami import fileutil
from leginon import leginondata
from leginon import projectdata
import time

class ImageCopier(object):
	def __init__(self,output_base_path):
		# output_base_path is the parent path of the session where the reference
		# images is to be copied
		if not os.path.isdir(output_base_path) or not os.access(output_base_path,os.W_OK):
			print '%s must exist and writable' % (output_base_path)
			sys.exit(1)
		self.output_base_path = output_base_path

	def saveImageFromImageData(self,datainst):
		old_image_path = datainst['session']['image path']
		bits = old_image_path.split(datainst['session']['name'])
		tail = bits[-1]
		# assumes that the path separator is '/'
		while tail[0] == '/':
			tail = tail[1:]
		new_image_path = os.path.join(output_base_path,datainst['session']['name']],tail)
		print new_image_path
		fileutil.mkdirs(new_image_path)
		filename = datainst['filename']+'.mrc'
		source = os.path.join(old_image_path,filename)
		destination = os.path.join(new_image_path,filename)
		shutil.copy(source,destination)

class SessionReferenceCopier(object):
	'''
	Copy References associated with a session name
	'''
	def __init__(self,sessionname, output_base_path):
		self.sessionname = sessionname
		self.setSession(sessionname)
		self.dbname = 'leginondata'
		self.setUpImageCopier(output_base_path)

	def setUpImageCopier(self,output_base_path):
		self.image_copier = ImageCopier(output_base_path)

	def hasImagesInSession(self):
		session = self.getSession()
		images = leginondata.AcquisitionImageData(session=session).query()
		return bool(images)

	def setSession(self, sessionname):
		q = leginondata.SessionData(name=sessionname)
		r = q.query(results=1)[0]
		if r:
			self.session = r[0]
		else:
			print 'No session named %s' % (sessionname,)
			sys.exit(1)

	def getSession(self):
		'''
		Get Session data reference.
		'''
		return self.session

	def getReferenceIds(self):
		print "Finding References...."
		q = leginondata.AcquisitionImageData(session=self.session)
		images = q.query()

		self.refids = {}
		for reftype in ('bright','dark','norm'):
			self.refids[reftype] = []
			for image in images:
				if image[reftype] is not None and image[reftype].dbid not in refids[reftype]:
					self.refids[reftype].append(image[reftype].dbid)
					if reftype == 'norm':
						bright_from_norm = self.findBrightImageFromNorm(image[reftype])
						if bright_from_norm and bright_from_norm.dbid not in self.refids['bright']:
							self.refids['bright'].append(bright_from_norm.dbid)

	def isInImageSession(self,refdata):
		ref_sessionid = refdata['session'].dbid
		image_sessionid = self.session.dbid
		return (ref_sessionid == image_sessionid)

	def copyRefImages(self):
		for reftype in ('bright','dark','norm'):
			for refid in self.refids[reftype]:
				classname = reftype[0].upper()+reftype[1:]+'ImageData'
				refdata = getattr(leginondata,classname)().direct_query(refid)
				if not self.isInImageSession(refdata):
					# ref images in the image session would be copied when the image session is copied
					# Only do the ones not in the image session
					self.image_copier.saveImageFromImageData(self,refdata)

	def run(self):
		image_sessiondata = self.getSourceSession()

		print "****Session %s ****" % (image_sessiondata['name'])
		if self.hasImagesInSession():
			self.getReferenceIds()
			self.copyRefImages()
		print ''

def copyProjectReferences(projectid,destination_base_path):
	'''
	Copy all sessions in the project identified by id number
	'''
	from leginon import projectdata
	p = projectdata.projects().direct_query(projectid)
	source_sessions = projectdata.projectexperiments(project=p).query()
	session_names = map((lambda x:x['session']['name']),source_sessions)
	session_names.reverse()  #oldest first
	print session_names
	
	for session_name in session_names[-1:]:
		app = SessionReferenceCopier(session_name,destination_base_path)
		app.run()
		app = None

if __name__ == '__main__':
	import sys
	if len(sys.argv) != 2:
		print "Usage: python copy_project_references.py <project id number> <destination base path"
		print " destination base path is the path before dividing by sessionname"
		print " For example, '/archive/leginon/'
		sys.exit()
	projectid = int(sys.argv[1])

	copyProjectReference(projectid)
