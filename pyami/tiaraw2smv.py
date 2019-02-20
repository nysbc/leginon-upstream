#!/usr/bin/env python
'''
This is for converting Ceta TIA raw output to SMV format.
'''
print('''This converts a series of TIA raw output *.bin to smv format''')
input_pattern= raw_input('Enter bin file prefix prior to _001.bin, for example: ')
output_pattern=raw_input('Enter smv file prefix: ')
offset_txt = raw_input('Data offset value (default=200 is added to the input value): ')
if offset_txt == '':
	offset = 200
else:
	offset = int(truncation_txt)

from pyami import tiaraw, numsmv

import os
import sys
test_filename = '%s_%03d.bin' % (input_pattern, 1)
if not os.path.isfile(test_filename):
	sys.exit('%s does not exist!' % test_filename)

import glob
filelist = glob.glob('%s_*.bin' % (input_pattern,))
total=len(filelist)

def read(fobj,start,shape,dtype):
		fobj.seek(start)
		datalen = shape[0]*shape[1]
		a = numpy.fromfile(fobj, dtype=dtype, count=datalen)
		a = numpy.reshape(a,shape)
		return a

for i in range(total):
	in_name='%s_%03d.bin' % (input_pattern, i+1)
	out_name='%s_%03d.img' % (output_pattern, i+1)
	data = tiaraw.read(in_name)
	numsmv.write(data,out_name, offset=offset)

