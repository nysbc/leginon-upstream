
## python
import time
import os
## PIL
#import Image
## spider
import spyder
## appion
import apImage
import apEMAN
import apParam
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
def refFreeAlignParticles(stackfile, template, numpart, pixrad,
		firstring=2, lastring=100, dataext=".spi"):
	"""
	inputs:
		stack
		template
		search params
	outputs:
		aligned stack
		rotation/shift params
	"""
	### setup
	if dataext in template:
		template = template[:-4]
	if dataext in stackfile:
		stackfile = stackfile[:-4]
	t0 = time.time()
	rundir = "alignment"
	apParam.createDirectory(rundir)

	### remove previous iterations
	numiter = 0
	while os.path.isfile(rundir+"/avgimg%03d%s" % (numiter+1, dataext)):
		os.remove(rundir+"/avgimg%03d%s" % (numiter+1, dataext))
		pngfile = rundir+"/avgimg%03d%s" % (numiter+1, ".png")
		if os.path.isfile(pngfile):
			os.remove(pngfile)
		numiter += 1

	### perform alignment
	mySpider = spyder.SpiderSession(dataext=dataext)
	# copy template to memory
	mySpider.toSpiderQuiet("CP", (template+"@1"), "_9") 
	mySpider.toSpider("AP SR", 
		stackfile+"@*****", "1-"+str(numpart), 
		str(int(pixrad)), str(int(firstring))+","+str(int(lastring)), 
		"_9", rundir+"/avgimg***", rundir+"/paramdoc***")
	mySpider.close()

	### find number of iterations
	numiter = 0
	while os.path.isfile(rundir+"/avgimg%03d%s" % (numiter+1, dataext)):
		emancmd = ("proc2d "
			+" "+rundir+"/avgimg"+("%03d%s" % (numiter+1, dataext))
			+" "+rundir+"/avgimg"+("%03d%s" % (numiter+1, ".png"))
		)
		apEMAN.executeEmanCmd(emancmd, verbose=False, showcmd=False)
		numiter += 1
	if numiter == 0:
		apDisplay.printError("alignment failed")
	apDisplay.printMsg(str(numiter)+" alignment iterations were run by spider")

	### convert spider rotation, shift data to python

	### write aligned stack -- with python loop
	### I tried this loop in both spider and python: python was faster?!? -neil
	mySpider = spyder.SpiderSession(dataext=dataext, logo=False)
	for p in range(1,numpart+1):
		mySpider.toSpiderQuiet(
			"UD IC,"+str(p)+",x21,x22,x23",
			(rundir+"/paramdoc%03d" % (numiter)),
			"RT SQ",
			stackfile+"@"+("%05d" % (p)),
			"alignedstack@"+("%05d" % (p)),
			"x21", "x22,x23")
	mySpider.close()
	td1 = time.time()-t0

	apDisplay.printMsg("completed alignment of "+str(numpart)
		+" particles in "+apDisplay.timeString(td1))

	return "alignedstack.spi"

#===============================
def refBasedAlignParticles(stackfile, templatestack, 
		xysearch, xystep, 
		numpart, numtemplate,
		firstring=2, lastring=100, 
		dataext=".spi"):
	"""
	inputs:
		stack
		template
		search params
	outputs:
		aligned stack
		rotation/shift params
	"""
	### setup
	if dataext in template:
		template = template[:-4]
	if dataext in stackfile:
		stackfile = stackfile[:-4]
	t0 = time.time()
	rundir = "alignment"
	apParam.createDirectory(rundir)

	### remove previous iterations

	### perform alignment
	mySpider = spyder.SpiderSession(dataext=dataext)
	# copy template to memory
	mySpider.toSpider("AP MQ", 
		templatestack+"@***",                       # reference image series
		"1-"+str(numtemplate),                      # enter number of templates of doc file
		str(int(xysearch))+","+str(int(xystep)),    # translation search range, step size
		str(int(firstring))+","+str(int(lastring)), # first and last ring for rotational correlation
		stackfile+"@*****",                         # unaligned image series
		"1-"+str(numpart),                          # enter number of particles of doc file
		rundir+"/paramdoc***",                      # output angles document file
	)
	mySpider.close()

	### find number of iterations

	### convert spider rotation, shift data to python

	### write aligned stack -- with python loop
	### I tried this loop in both spider and python: python was faster?!? -neil
	mySpider = spyder.SpiderSession(dataext=dataext, logo=False)
	for p in range(1,numpart+1):
		mySpider.toSpiderQuiet(
			"UD IC,"+str(p)+",x21,x22,x23",
			(rundir+"/paramdoc%03d" % (numiter)),
			"RT SQ",
			stackfile+"@"+("%05d" % (p)),
			"alignedstack@"+("%05d" % (p)),
			"x21", "x22,x23")
	mySpider.close()
	td1 = time.time()-t0

	apDisplay.printMsg("completed alignment of "+str(numpart)
		+" particles in "+apDisplay.timeString(td1))

	return "alignedstack.spi"

#===============================
def correspondenceAnalysis(alignedstack, boxsize, maskrad, numpart, numfactors=20, dataext=".spi"):
	"""
	inputs:
		aligned stack
		search params
	outputs:
		eigen images
		eigen vectors
		coran parameters
	"""
	### setup
	if dataext in alignedstack:
		alignedstack = alignedstack[:-4]
	t0 = time.time()
	rundir = "coran"
	apParam.createDirectory(rundir)

	### make template in memory
	mySpider = spyder.SpiderSession(dataext=dataext)
	mySpider.toSpiderQuiet("MO", "_9", "%d,%d" % (boxsize, boxsize), "C", str(maskrad))

	### performing correspondence analysis
	apDisplay.printMsg("Performing correspondence analysis (long wait)")
	mySpider.toSpider(
		"CA S",
		alignedstack+"@*****", "1-"+str(numpart),
		"_9", str(numfactors), "C", "10",
		rundir+"/corandata")

	### generate eigen images
	for fact in range(1,numfactors+1):
		mySpider.toSpiderQuiet(
			"CA SRE", rundir+"/corandata", str(fact), 
			rundir+"/eigenimg@"+("%03d" % (fact)), )
	mySpider.close()

	"""
	output file info:
	==================
	* _SEQ :: Unformatted sequential file having image values under the mask. 
	* _SET :: Transposed direct access file having image values under the mask.
	* _MAS :: Mask FILE in SPIDER image format 
	* _IMC :: Text file with image coordinates.
		NUMIM, NFAC, NSAM, NROW, NUMIM, PCA
		IMAGE(1) COORDINATES (1..NFAC), WEIGHTP(1), DOR, FIM(1)
	* _PIX :: Text file with pixel coordinates.
		NPIX, NFAC, NSAM , NROW , NUMIM, PCA
		PIXEL(1) COORDINATES (1..NFAC), WEIGHTP(1), CO(1), FPIX
	* _EIG :: Text file with eigenvalues.
		NFAC, TOTAL WEIGHT, TRACE, PCA, N
		EIGENVALUE(1), %, CUMULATIVE %
	"""
	### remove worthless temporary files
	for tail in ["_SEQ", "_SET", "_MAS", "_PIX",]:
		if os.path.isfile(rundir+"/corandata"+tail+dataext):
			os.remove(rundir+"/corandata"+tail+dataext)

	eigf = open(rundir+"/corandata_EIG"+dataext, "r")
	count = 0
	for line in eigf:
		bits = line.strip().split()
		if len(bits) == 3:
			count += 1
			print count, float(bits[1]), float(bits[2]), float(bits[0])

	### make nice pngs for webpage
	for fact in range(1,numfactors+1):
		emancmd = ("proc2d "+rundir+"/eigenimg.spi "
			+rundir+"/eigenimg"+("%03d" % (fact))+".png "
			+" first="+str(fact-1)+" last="+str(fact-1))
		apEMAN.executeEmanCmd(emancmd, verbose=False, showcmd=False)

	### convert SPIDER image to IMAGIC for webpage
	eigenimg = rundir+"/eigenimg.hed"
	if os.path.isfile(eigenimg):
		os.remove(eigenimg)
		os.remove(eigenimg[:-4]+".img")
	emancmd = "proc2d "+rundir+"/eigenimg.spi "+eigenimg
	apEMAN.executeEmanCmd(emancmd, verbose=False, showcmd=True)

	td1 = time.time()-t0
	apDisplay.printMsg("completed correspondence analysis of "+str(numpart)
		+" particles in "+apDisplay.timeString(td1))

	return




