#
# COPYRIGHT:
#       The Leginon software is Copyright 2003
#       The Scripps Research Institute, La Jolla, CA
#       For terms of the license agreement
#       see  http://ami.scripps.edu/software/leginon-license
#

"""
leginonconfig.py: Configuration file for leginon defaults and such
We could also do this using the ConfigParser module and have this
be a more standard .ini file thing.
"""

import errno
import os

#############################################################
#   utility functions and exceptions used in this script    #
#     (do not change any of this, skip to next section)     #
#############################################################

pathmapping = {}
def mapPath(path):
		if not pathmapping:
			return path

		for key, value in pathmapping.items():
			if value == path[:len(value)]:
				path = key + path[len(value):]
				break

		return path

# Here is a replacement for os.mkdirs that won't complain if dir
# already exists (from Python Cookbook, Recipe 4.17)
def mkdirs(newdir, mode=0777):
	try: os.makedirs(newdir, mode)
	except OSError, err:
		if err.errno != errno.EEXIST or not os.path.isdir(newdir):
			raise
### raise this if something is wrong in this config file
class LeginonConfigError(Exception):
	pass

#########################
#	Database	#
#########################
## fill in your database and user info
DB_HOST = ''
DB_NAME = ''
DB_USER = ''
DB_PASS = ''

## check if DB is configured (DB_PASS can be '')
if '' in (DB_HOST, DB_NAME, DB_USER):
	raise LeginonConfigError('need database info in leginonconfig.py')

# This is optional.  If not using a project database, leave DB_PROJECT_HOST
# set to 'none', and the other DB_PROJECT_ variables blank.
DB_PROJECT_HOST = 'none'
DB_PROJECT_NAME = ''
DB_PROJECT_USER = ''
DB_PROJECT_PASS = ''

#########################
#        Paths          #
#########################
## use os.getcwd() for current directory

## IMAGE_PATH is a base directory, a session subdirectory will 
## automatically be created when the first image is saved
IMAGE_PATH	= ''
HOME_PATH	= os.path.expanduser('~')
ID_PATH		= os.path.join(HOME_PATH, '.leginon', 'ids')

if not IMAGE_PATH:
	raise LeginonConfigError('set IMAGE_PATH in leginonconfig.py')

## create those paths
try:
	mkdirs(mapPath(IMAGE_PATH))
except:
	print 'error creating IMAGE_PATH %s' % (IMAGE_PATH,)

USERNAME = ''

