#!/usr/bin/python -O

import sys
import os
import Mrc
import imagefun
import numarray
import numarray.nd_image as nd_image
import numarray.convolve as convolve
import numarray.fft as fft
import Image
import ImageDraw
import numextension
import string
import math
import convolver
import numarray.random_array as random_array
import numarray.linear_algebra as linear_algebra
import selexonFunctions

def runCrossCorr(params,file):
	# Run Neil's version of FindEM
	imagefile = file+".mrc"
	tmplt     =params["template"]

	#CYCLE OVER EACH TEMPLATE
	classavg=1
	while classavg<=len(params['templatelist']):
		print "Template ",classavg
		outfile="cccmaxmap%i00.mrc" % classavg
		if (os.path.exists(outfile)):
			print " ... removing outfile:",outfile
			os.remove(outfile)

		if (params["multiple_range"]==True):
			strt=float(params["startang"+str(classavg)])
			end=float(params["endang"+str(classavg)])
			incr=float(params["incrang"+str(classavg)])
		else:
			strt=float(params["startang"])
			end=float(params["endang"])
			incr=float(params["incrang"])

		if (len(params['templatelist'])==1 and not params['templateIds']):
			templfile = tmplt+".mrc"
		else:
			templfile = tmplt+str(classavg)+".mrc"

		#MAIN FUNCTION HERE:
		createCrossCorr(params,imagefile,templfile,outfile,strt,end,incr)

		classavg+=1
	return


def createCrossCorr(params, imagefile, templfile, outfile, strt, end, incr):
	bin     = int(params["bin"])
	apix    = float(params["apix"])
	diam    = float(params["diam"])
	lowpass	= float(params["lp"])
	pixrad  = diam/apix/2.0

	#READ IMAGES
	image    = Mrc.mrc_to_numeric(imagefile)
	template = Mrc.mrc_to_numeric(templfile)

	#BIN IMAGES
	image    = imagefun.bin(image,bin)
	templatebin = imagefun.bin(template,bin) #FAKE FOR SIZING

	#NORMALIZE
	image    = normStdev(image)
	image    = PlaneRegression(image)
	image    = normStdev(image)
	template = normStdev(template)

	#LOW PASS FILTER
	image    = selexonFunctions.filterImg(image,apix*float(bin),lowpass)

	#BLACK OUT DARK AREAS, LESS THAN 2 STDEVS
	image = removeCrud(image,imagefile,-1.5,params)

	#MASK IF YOU WANT
	#tmplmask = circ_mask(template,diam/apix)
	#template = template*tmplmask

	crossmax = 0*image-10
	#normmax  = crossmax
	#crossmin = 0*image+10
	#crossavg = 0*image
	#crossstd = 0*image
	imagefft = calc_imagefft(image,templatebin) #SAVE SOME CPU CYCLES
	ang = strt
	i = 1

	print "Starting rotations ... "
	totalrots = int( (end - strt) / incr + 0.999)
	while(ang < end):
		print " ... rotation:",i,"of",totalrots,"  \tangle =",ang
		template2   = nd_image.rotate(template,ang,reshape=False,mode="wrap")
		#template3   = nd_image.gaussian_filter(template2,sigma=int(pixrad/5.0+1.0),mode="wrap")
		#template3   = nd_image.median_filter(template2,size=rad,mode="wrap")
		#template3   = selexonFunctions.filterImg(template2,apix,diam*apix/4.0)
		#numeric_to_jpg(template2,"template2.jpg")
		#numeric_to_jpg(template3,"template3.jpg")
		template2   = imagefun.bin(template2,bin)
		#template3   = imagefun.bin(template3,bin)

		templatefft  = calc_templatefft(image,template2)
		#templatefft3 = calc_templatefft(image,template3)
		cross        = cross_correlate_fft(image,template2,imagefft,templatefft)
		#norm         = cross_correlate_fft(image,template3,imagefft,templatefft3)
		#cross       = cross_correlate(image,template2) #CLASSIC CALCULATION
		del template2
		del templatefft
		#del template3
		#del templatefft3
		#cross       = normRange(cross)
		#norm        = normRange(norm)

		crossmax    = numarray.where(cross>crossmax,cross,crossmax)
		#normmax     = numarray.where(norm>normmax,norm,normmax)
		#crossmin    = numarray.where(cross<crossmin,cross,crossmin)
		#crossavg    = crossavg + cross
		#crossstd    = crossstd + cross * cross

		del cross
		#del norm

		ang = ang + incr
		i = i + 1

	#CREATE BEST FILTERED IMAGE
	rad = int(diam/apix/bin/2+1)
	#crossmed    = nd_image.minimum_filter(crossmax,size=3)
	#crossmed    = nd_image.median_filter(crossmed,size=rad)
	#crossnorm   = crossmax - normmax
	#crossnorm   = crossmax
	#del crossmed

	#crossnorm   = nd_image.median_filter(crossnorm,size=3)
	crossmax   = normRange(crossmax)
	#crossnorm   = normRange(crossnorm)
	#NORMalized = MAXimum - MEDian (WORKS?)

	#crossavg    = crossavg / rot
	#crossstd    = (crossstd - rot * crossavg * crossavg) / (rot - 1)

	#REMOVE OUTSIDE AREA
	cutrad = int(diam/apix/float(bin)/2.0)
	#cutrad = (templatebin.shape)[0]/2 #ASSUME TEMPLATE IS SQUARE!
	cshape = crossmax.shape
 	crossmax[ 0:cutrad, 0:cshape[1] ] = 0.1
	crossmax[ 0:cshape[0], 0:cutrad ] = 0.1
 	crossmax[ cshape[0]-cutrad:cshape[0], 0:cshape[1] ] = 0.1
	crossmax[ 0:cshape[0], cshape[1]-cutrad:cshape[1] ] = 0.1

	Mrc.numeric_to_mrc(crossmax,outfile)
	#numeric_to_jpg(crossmed,"crossmed.jpg")
	numeric_to_jpg(crossmax,imagefile+"-ccmaxmap.jpg")
	#numeric_to_jpg(crossnorm,outfile+".jpg")
	#numeric_to_jpg(crossmax,"crossmax.jpg")
	#numeric_to_jpg(normmax,"normmax.jpg")
	#numeric_to_jpg(crossstd2,"crossstd.jpg")
	#numeric_to_jpg(crossmin,"crossmin.jpg")
	#numeric_to_jpg(crossavg,"crossavg.jpg")
	#del crossnorm
	del crossmax
	#del normmax


def removeCrud(image,imagefile,stdev,params):
	print "Put noise in low density regions (crud remover)"

	bin     = int(params["bin"])
	apix    = float(params["apix"])
	diam    = float(params["diam"])
	lowpass	= float(params["lp"])
	pixrad  = diam/apix/2.0/float(bin)/4

	#BLACK OUT DARK AREAS, LESS THAN 2 STDEVS

	print " ... low pass filter"
	#imagemed = selexonFunctions.filterImg(image,apix*float(bin),int(pixrad+1))
	imagemed = filterImg(image,apix*float(bin),int(16*pixrad+1))

	print " ... max/min filters"
	#GROW
	print " ... ... grow filter"
	rad = int(pixrad/2+1)
	def distsq(x,y):
		return (x-rad)**2 + (y-rad)**2
	fp = numarray.fromfunction(distsq, (rad*2,rad*2))
	fp = numarray.where(fp < rad**2,1.0,0.0)
	imagemed = nd_image.minimum_filter(imagemed, \
		footprint=fp,mode="constant",cval=stdev)
	#SHRINK
	print " ... ... shrink filter"
	rad = int(pixrad+1)
	def distsq(x,y):
		return (x-rad)**2 + (y-rad)**2
	fp = numarray.fromfunction(distsq, (rad*2,rad*2))
	fp = numarray.where(fp < rad**2,1.0,0.0)
	imagemed = nd_image.maximum_filter(imagemed, \
		footprint=fp,mode="constant",cval=0.0)
	#GROW
	print " ... ... grow filter"
	rad = int(2*pixrad+1)
	def distsq(x,y):
		return (x-rad)**2 + (y-rad)**2
	fp = numarray.fromfunction(distsq, (rad*2,rad*2))
	fp = numarray.where(fp < rad**2,1.0,0.0)
	imagemed = nd_image.minimum_filter(imagemed, \
		footprint=fp,mode="constant",cval=stdev)

	#SHRINK
	print " ... ... shrink filter"
	rad = int(pixrad/2+1)
	def distsq(x,y):
		return (x-rad)**2 + (y-rad)**2
	fp = numarray.fromfunction(distsq, (rad*2,rad*2))
	fp = numarray.where(fp < rad**2,1.0,0.0)
	imagemed = nd_image.maximum_filter(imagemed, \
		footprint=fp,mode="constant",cval=0.0)

	imagemed = normStdev(imagemed)
	print " ... create mask"
	imagemask = numarray.where(imagemed>stdev,0.0,1.0)
	#numeric_to_jpg(imagemask,imagefile+"-mask.jpg")
	#image = numarray.where(imagemask<0.1,image,image-3)
	print " ... create random noise data"
	imagerand = random_array.normal(0.0, 1.0, shape=image.shape)
	print " ... replace crud with noise"
	image = numarray.where(imagemask<0.1,image,imagerand) #random.gauss(-1.0,1.0))
	#numeric_to_jpg(image,imagefile+"-modified.jpg")
	del imagemed
	del imagemask
	del imagerand
	return image


def filterImg(img,apix,res):
	# low pass filter image to res resolution
	if res==0:
		print "Skipping low pass filter"
		return(img)
	else:
		sigma=(res/apix)/3.0
		kernel=convolver.gaussian_kernel(sigma)
		#Mrc.numeric_to_mrc(kernel,'kernel.mrc')
	#return(convolve.convolve2d(img,kernel,fft=1,mode='reflect'))
	c=convolver.Convolver()
	return(c.convolve(image=img,kernel=kernel))

def PlaneRegression(sqarray):
	print " ... calculate 2d linear regression"
	if ( (sqarray.shape)[0] != (sqarray.shape)[1] ):
		print "Array is NOT square"
		sys.exit(1)
	size = (sqarray.shape)[0]
	count = float((sqarray.shape)[0]*(sqarray.shape)[1])
	def retx(y,x):
		return x
	def rety(y,x):
		return y	
	xarray = numarray.fromfunction(retx, sqarray.shape)
	yarray = numarray.fromfunction(rety, sqarray.shape)
	xsum = float(xarray.sum())
	xsumsq = float((xarray*xarray).sum())
	ysum = xsum
	ysumsq = xsumsq
	xysum = float((xarray*yarray).sum())
	xzsum = float((xarray*sqarray).sum())
	yzsum = float((yarray*sqarray).sum())
	zsum = sqarray.sum()
	zsumsq = (sqarray*sqarray).sum()
	xarray = xarray.astype(numarray.Float64)
	yarray = yarray.astype(numarray.Float64)
	leftmat = numarray.array( [[xsumsq, xysum, xsum], [xysum, ysumsq, ysum], [xsum, ysum, count]] )
	rightmat = numarray.array( [xzsum, yzsum, zsum] )
	resvec = linear_algebra.solve_linear_equations(leftmat,rightmat)
	print " ... plane_regress: x-slope:",round(resvec[0]*size,5),\
		", y-slope:",round(resvec[1]*size,5),", xy-intercept:",round(resvec[2],5)
	return sqarray - xarray*resvec[0] - yarray*resvec[1] - resvec[2]
	sys.exit(1)


def findPeaks2(params,file):
	#Does NOT use viewit
	#Resulting in a 5-fold speed up over findPeaks()

	numtempl =    len(params['templatelist'])
	bin =         int(params["bin"])
	diam =        float(params["diam"])
	apix =        float(params["apix"])
	#MAXBLOBSIZE ==> 1/8 AREA OF PARTICLE
	maxblobsize = int(round(math.pi*(apix*diam/float(bin))**2/32.0,0))+1

	blobs = []
	for i in range(numtempl):
		blobs.append(findPeaksInMap(file,i+1,params,maxblobsize))

	mergePikFiles(file,blobs,params)

	return


def findPeaksInMap(file,num,params,maxblobsize):

	threshold =   float(params["thresh"])
	bin =         int(params["bin"])
	diam =        float(params["diam"])
	apix =        float(params["apix"])
	olapmult =    float(params["overlapmult"])

	print " ... threshold",threshold

	infile="cccmaxmap"+str(num)+"00.mrc"
	outfile="pikfiles/"+file+"."+str(num)+".pik"
	if (os.path.exists(outfile)):
		os.remove(outfile)
		print " ... removed existing file:",outfile

	cc=Mrc.mrc_to_numeric(infile)
	cc2=imagefun.threshold(cc,threshold)

	#Mrc.numeric_to_mrc(cc2,"threshold.mrc")

	#for i in range(30):
	#	thresh = threshold + float(i-15)*0.01
	#	cc2=imagefun.threshold(cc,thresh)
	#	blobs = imagefun.find_blobs(cc,cc2,6,3000,60,1)
	#	print thresh," ",len(blobs)

	blobs = imagefun.find_blobs(cc,cc2,6,3000,maxblobsize,0)
	#find_blobs(image,mask,border,maxblobs,maxblobsize,minblobsize)
	print "Template "+str(num)+": Found",len(blobs),"peaks"

	cutoff = olapmult*diam*0.5/float(bin)/apix	#1.5x particle radius in pixels
	removeOverlappingBlobs(blobs,cutoff)

	blobs.sort(blob_compare)

	f=open(outfile, 'w')
	for blob in blobs:
		row = blob.stats['center'][0]
		column = blob.stats['center'][1]
		mean = blob.stats['mean']
		std = blob.stats['stddev']
		size = blob.stats['n']
		mean_str = "%.4f" % mean
		std_str = "%.4f" % std
		out = file+".mrc "+str(int(column)*bin)+" "+str(int(row)*bin)+ \
			" "+mean_str+" "+std_str+" "+str(int(size))
		f.write(str(out)+"\n")
	f.close()

	return blobs


def blob_compare(x,y):
	if float(x.stats['mean']) < float(y.stats['mean']):
		return 1
	else:
		return -1


def removeOverlappingBlobs(blobs,cutoff):
	#distance in pixels for two blobs to be too close together
	print " ... overlap distance cutoff:",round(cutoff,1),"pixels"
	cutsq = cutoff**2+1

	initblobs = len(blobs)
	blobs.sort(blob_compare)
	i=0
	while i < len(blobs):
		j=0
		while j < i:
			distsq = blob_distsq((blobs)[i],(blobs)[j])
			if(distsq < cutsq):
				del blobs[i]
				i=i-1
				j=j-1
			j=j+1
		i=i+1
	postblobs = len(blobs)
	print " ... kept",postblobs,"non-overlapping particles of",initblobs,"total particles"
	return blobs


def mergePikFiles(file,blobs,params):
	print "Merging #.pik files into a.pik file"
	bin =         int(params["bin"])
	diam =        float(params["diam"])
	apix =        float(params["apix"])
	olapmult =    float(params["overlapmult"])

	outfile="pikfiles/"+file+".a.pik"
	if (os.path.exists(outfile)):
		os.remove(outfile)
		print " ... removed existing file:",outfile

	#PUT ALL THE BLOBS IN ONE ARRAY
	allblobs = []
	for i in range(len(blobs)):
		allblobs.extend(blobs[i])

	#REMOVE OVERLAPPING BLOBS
	cutoff = olapmult*diam*0.5/float(bin)/apix	#1.5x particle radius in pixels
	allblobs = removeOverlappingBlobs(allblobs,cutoff)

	#WRITE SELECTED BLOBS TO FILE
	f=open(outfile, 'w')
	for i in range(len(blobs)):
		for blob in (blobs[i]):
			if blob in allblobs:
				row = blob.stats['center'][0]
				column = blob.stats['center'][1]
				mean = blob.stats['mean']
				std = blob.stats['stddev']
				size = blob.stats['n']
				mean_str = "%.4f" % mean
				std_str = "%.4f" % std
				out = file+".mrc "+str(int(column)*bin)+" "+str(int(row)*bin)+ \
					" "+mean_str+" "+std_str+" "+str(int(size))+" "+str(i)
				f.write(str(out)+"\n")
	f.close()
	return


def blob_distsq(x,y):
	row1 = x.stats['center'][0]
	col1 = x.stats['center'][1]
	row2 = y.stats['center'][0]
	col2 = y.stats['center'][1]
	return (row1-row2)**2+(col1-col2)**2


def createJPG2(params,file):
	#Does NOT use viewit
	#Resulting in a 2-fold speed up over createJPG()
	#With more features!!!

	mrcfile = file+".mrc"
	count =   len(params['templatelist'])
	bin =     int(params["bin"])/2
	diam =    float(params["diam"])
	apix =    float(params["apix"])
	if bin < 1: 
		bin = 1
	if not (os.path.exists("jpgs")):
		os.mkdir("jpgs")

	#print "Reading MRC: ",mrcfile
	numer=Mrc.mrc_to_numeric(mrcfile)
	numer=numextension.bin(numer,bin)

	#print "Image: ",numer.getshape()
	numer=normalizeImage(numer)
	image2 = array2image(numer)
	image2 = image2.convert("RGB")

	pikfile="pikfiles/"+file+".a.pik"
	print " ... reading Pik: ",pikfile
	draw = ImageDraw.Draw(image2)
	#blend(image1,image2,0.5)
	draw = readPikFile(pikfile,draw,diam,bin,apix) 
	del draw

	
	outfile="jpgs/"+mrcfile+".prtl.jpg"
	print " ... writing JPEG: ",outfile
	image2.save(outfile, "JPEG", quality=95)


def normalizeImage(a):
	"""	
	Normalizes numarray to fit into an image format
	that is values between 0 and 255.
	"""
#Minimum image value, i.e. how black the image can get
	minlevel = 0.0
#Maximum image value, i.e. how white the image can get
	maxlevel = 235.0
#Maximum standard deviations to include, i.e. pixel > N*stdev --> white
	devlimit=5.0
 	imrange = maxlevel - minlevel

	avg1=nd_image.mean(a)

	stdev1=nd_image.standard_deviation(a)

	min1=nd_image.minimum(a)
	if(min1 < avg1-devlimit*stdev1):
		min1 = avg1-devlimit*stdev1

	max1=nd_image.maximum(a)
	if(max1 > avg1+devlimit*stdev1):
		max1 = avg1+devlimit*stdev1

	c = (a - min1)/(max1 - min1)*imrange + minlevel
	c = numarray.where(c > maxlevel,255.0,c)
	c = numarray.where(c < minlevel,0.0,c)

	return c


def array2image(a):
    """
    Converts array object (numarray) to image object (PIL).
    """
    h, w = a.shape[:2]
    int32 = numarray.Int32
    uint32 = numarray.UInt32
    float32 = numarray.Float32
    float64 = numarray.Float64

    if a.type()==int32 or a.type()==uint32 or a.type()==float32 or a.type()==float64:
        a = a.astype(numarray.UInt8) # convert to 8-bit
    if len(a.shape)==3:
        if a.shape[2]==3:  # a.shape == (y, x, 3)
            r = Image.fromstring("L", (w, h), a[:,:,0].tostring())
            g = Image.fromstring("L", (w, h), a[:,:,1].tostring())
            b = Image.fromstring("L", (w, h), a[:,:,2].tostring())
            return Image.merge("RGB", (r,g,b))
        elif a.shape[2]==1:  # a.shape == (y, x, 1)
            return Image.fromstring("L", (w, h), a.tostring())
    elif len(a.shape)==2:  # a.shape == (y, x)
        return Image.fromstring("L", (w, h), a.tostring())
    else:
        raise ValueError, "unsupported image mode"


def readPikFile(file,draw,diam,bin,apix):
	"""	
	Reads a .pik file and draw circles around all the points
	in the .pik file
	"""
	circle_colors = [ \
		"#f2f23d","#3df2f2","#f23df2", \
		"#ff4040","#3df23d","#3d3df2", \
		"#f2973d","#3df297","#973df2", \
		"#97f23d","#3d97f2","#f23d97", ]
	"""	
	Order: 	Yellow, Cyan, Magenta, Red, Green, Blue,
		Orange, Teal, Purple, Lime-Green, Sky-Blue, Pink
	"""
	dscale=1 #variable to scale particle radius, can be a commandline option later
	ps=int(dscale*diam*0.5/float(bin)/apix) 
	ps=float(dscale*diam*0.5/float(bin)/apix) 
	f=open(file, 'r')
	for line in f:
		line=string.rstrip(line)
		bits=line.split(' ')
		#x1=int(bits[1])/bin
		#y1=int(bits[2])/bin
		x1=float(bits[1])/float(bin)
		y1=float(bits[2])/float(bin)
		coord=(x1-ps, y1-ps, x1+ps, y1+ps)
		if(len(bits) > 6):
			num = int(bits[6])%12
		else:
			num = 0
		draw.ellipse(coord,outline=circle_colors[num])
		#draw.rectangle(coord,outline=color1)
	f.close()
	return draw

def circ_mask(numer,pixrad):
	indices = numarray.indices(numer.shape)
	x0, y0 = (numer.shape)[0]/2, (numer.shape)[1]/2
	dx, dy = indices[0]-y0,indices[1]-x0
	return numarray.sqrt(dx**2+dy**2)<pixrad


def numeric_to_jpg(numer,file):
	numer=normalizeImage(numer)
	image = array2image(numer)
	#image = image.convert("RGB")
	print " ... writing JPEG: ",file
	image.save(file, "JPEG", quality=85)

def normRange(im):
	min1=nd_image.minimum(im)
	max1=nd_image.maximum(im)
	return (im - min1)/(max1 - min1)

def normStdev(im):
	avg1=nd_image.mean(im)
	std1=nd_image.standard_deviation(im)
	return (im - avg1)/std1

def cross_correlate(image,template):	
	#CALCULATE BIGGER MAP SIZE
	shape = image.shape
	kshape = template.shape
	oversized = (numarray.array(shape) + numarray.array(kshape))

	#EXPAND IMAGE TO BIGGER SIZE
	avg=nd_image.mean(image)
	image2 = convolve.iraf_frame.frame(image, oversized, mode="constant", cval=avg)

	#CALCULATE FOURIER TRANSFORMS
	imagefft = fft.real_fft2d(image2, s=oversized)
	del image2
	templatefft = fft.real_fft2d(template, s=oversized)

	#MULTIPLY FFTs TOGETHER
	newfft = imagefft * templatefft 
	del imagefft
	del templatefft

	#INVERSE TRANSFORM TO GET RESULT
	correlation = fft.inverse_real_fft2d(newfft, s=oversized)
	del newfft

	#RETURN CENTRAL PART OF IMAGE (SIDES ARE JUNK)
	return correlation[ kshape[0]-1:shape[0]+kshape[0]-1, kshape[1]-1:shape[1]+kshape[1]-1 ]


def calc_templatefft(image, template):
	#CALCULATE BIGGER MAP SIZE
	shape = image.shape
	kshape = template.shape
	oversized = (numarray.array(shape) + numarray.array(kshape))

	#CALCULATE FOURIER TRANSFORMS
	templatefft = fft.real_fft2d(template, s=oversized)

	return templatefft


def calc_imagefft(image, template):
	#CALCULATE BIGGER MAP SIZE
	shape = image.shape
	kshape = template.shape
	oversized = (numarray.array(shape) + numarray.array(kshape))

	#EXPAND IMAGE TO BIGGER SIZE
	avg=nd_image.mean(image)
	image2 = convolve.iraf_frame.frame(image, oversized, mode="constant", cval=avg)

	#CALCULATE FOURIER TRANSFORMS
	imagefft = fft.real_fft2d(image2, s=oversized)
	del image2

	return imagefft


def cross_correlate_fft(image, template, imagefft, templatefft):
	#CALCULATE BIGGER MAP SIZE
	shape = image.shape
	kshape = template.shape
	oversized = (numarray.array(shape) + numarray.array(kshape))

	#MULTIPLY FFTs TOGETHER
	newfft = imagefft * templatefft 
	del templatefft

	#INVERSE TRANSFORM TO GET RESULT
	correlation = fft.inverse_real_fft2d(newfft, s=oversized)

	#RETURN CENTRAL PART OF IMAGE (SIDES ARE JUNK)
	return correlation[ kshape[0]-1:shape[0]+kshape[0]-1, kshape[1]-1:shape[1]+kshape[1]-1 ]


def phase_correlate(image, template):	
	#CALCULATE BIGGER MAP SIZE
	shape = image.shape
	kshape = template.shape
	oversized = (numarray.array(shape) + numarray.array(kshape))

	#EXPAND IMAGE TO BIGGER SIZE
	avg=nd_image.mean(image)
	image2 = convolve.iraf_frame.frame(image, oversized, mode="constant", cval=avg)

	#CALCULATE FOURIER TRANSFORMS
	imagefft = fft.real_fft2d(image2, s=oversized)
	templatefft = fft.real_fft2d(template, s=oversized)

	#MULTIPLY FFTs TOGETHER
	newfft = imagefft * templatefft 
	del templatefft

	#NORMALIZE CC TO GET PC
	phasefft = newfft / numarray.absolute(newfft)
	del newfft

	#INVERSE TRANSFORM TO GET RESULT
	correlation = fft.inverse_real_fft2d(phasefft, s=oversized)
	del phasefft

	#RETURN CENTRAL PART OF IMAGE (SIDES ARE JUNK)
	return correlation[ kshape[0]-1:shape[0]+kshape[0]-1, kshape[1]-1:shape[1]+kshape[1]-1 ]

def tmpRemoveCrud(params,imagefile):
	bin     = int(params["bin"])
	apix    = float(params["apix"])
	diam    = float(params["diam"])
	lowpass	= float(params["lp"])
	pixrad  = diam/apix/2.0
	
	imagefile=imagefile+'.mrc'
	#READ IMAGES
	image    = Mrc.mrc_to_numeric(imagefile)

	#BIN IMAGES
	image    = imagefun.bin(image,bin)

	#NORMALIZE
	image    = normStdev(image)
#	image    = PlaneRegression(image)
#	image    = normStdev(image)

	#LOW PASS FILTER
	image    = selexonFunctions.filterImg(image,apix*float(bin),lowpass)

	#BLACK OUT DARK AREAS, LESS THAN 2 STDEVS
	image = removeCrud(image,imagefile,-1.0,params)
	Mrc.numeric_to_mrc(image,(imagefile.split('.')[0]+'.dwn.mrc'))
	return()
