
## python
import time
import os
## appion
import apDisplay

"""
A large collection of SPIDER functions

I try to keep the trend
image file: 
	*****img.spi
doc/keep/reject file: 
	*****doc.spi
file with some data:
	*****data.spi

that way its easy to tell what type of file it is

neil
"""

#===============================
def spiderOutputLine(int1, int2, float1, float2, float3, float4, float5, float6=1.0):
	line = "%04d" % int1
	line += " %1d" % int2
	line += apDisplay.leftPadString("%4.6f" % float1, n=12)
	line += apDisplay.leftPadString("%4.6f" % float2, n=12)
	line += apDisplay.leftPadString("%4.6f" % float3, n=12)
	line += apDisplay.leftPadString("%4.6f" % float4, n=12)
	line += apDisplay.leftPadString("%4.6f" % float5, n=12)
	line += apDisplay.leftPadString("%4.6f" % float6, n=12)
	line += "\n"
	return line


#===============================
def spiderOutLine(num, floatlist):
	line = "%04d" % num
	line += " %1d" % len(floatlist)
	for fnum in floatlist:
		line += apDisplay.leftPadString("%4.6f" % fnum, n=12)
	line += "\n"
	return line


#===============================
def spiderInLine(line):
	bits = line.strip().split()
	rownum = int(bits[0])
	numfloats = int(bits[1])
	floatlist = []
	for i in range(numfloats):
		floatlist.append(float(bits[i+2]))
	spidict = {
		'row': rownum,
		'count': numfloats,
		'floatlist': floatlist,
	}
	return spidict

#===============================
def addParticleToStack(partnum, partfile, stackfile):
	mySpider = spyder.SpiderSession(dataext=dataext, logo=True)
	mySpider.toSpiderQuiet("CP", 
		partfile, #particle file
		stackfile+"@%06d"%(partnum), #stack file
	)
	mySpider.close()
	return spidict

#===============================
def addParticleToStack(stackfile, numpart, avgfile, varfile):
	mySpider = spyder.SpiderSession(dataext=dataext, logo=True)
	mySpider.toSpider("AS R", 
		partfile, #particle file
		stackfile+"@%06d"%(partnum), #stack file
	)
	mySpider.close()
	return spidict






