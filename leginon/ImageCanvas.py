#!/usr/bin/env python

from Tkinter import *
from NumericImage import *
import time

class ImageCanvas(Frame):
	def __init__(self, parent, *args, **kargs):
		Frame.__init__(self, parent, *args, **kargs)
		self.parent = parent
		self.__build()
		self.bindings()
		self.cursorinfo = CursorInfo(self)
		self.scalingwidget = None
		self.zoomingwidget = None
		self.numimage = None

	def displayMessage(self, message):
		self.canvas.itemconfigure(self.canmessage, text=message,state='normal')

	def deleteMessage(self):
		self.canvas.itemconfigure(self.canmessage, state='hidden')

	def bindings(self):
		self.canvas.bind('<Configure>', self.configure_callback)
		self.canvas.bind('<Motion>', self.motion_callback)
		self.canvas.bind('<Leave>', self.leave_callback)
		self.canvas.bind('<Enter>', self.enter_callback)

	def bindCanvas(self, event, func):
		self.canvas.bind(event, func)

	def __build(self):
		bgcolor = self['background']
		can = self.canvas = Canvas(self, bg=bgcolor)
		self.canimage = can.create_image(0, 0, anchor=NW)
		self.canmessage = can.create_text(20,20, anchor=NW, fill='blue', state='hidden')

		hs = self.hscroll = Scrollbar(self, orient=HORIZONTAL, background=bgcolor, troughcolor=bgcolor)
		vs = self.vscroll = Scrollbar(self, orient=VERTICAL, background=bgcolor, troughcolor=bgcolor)

		## connect canvas to scrollbars
		can.config(xscrollcommand=hs.set, yscrollcommand=vs.set)
		hs.config(command=can.xview)
		vs.config(command=can.yview)
		can.grid(row=0, column=0, sticky=NSEW)
		self.rowconfigure(0, weight=1)
		self.columnconfigure(0, weight=1)

		self.hscroll_state(ON)
		self.vscroll_state(ON)

	def hscroll_state(self, switch):
		if switch == ON:
			self.hscroll.grid(row=1, column=0, sticky=NSEW)
		elif switch == OFF:
			self.hscroll.grid_remove()
		self.scroll_switched = 1

	def vscroll_state(self, switch):
		if switch == ON:
			self.vscroll.grid(row=0, column=1, sticky=NSEW)
		elif switch == OFF:
			self.vscroll.grid_remove()
		self.scroll_switched = 1

	def configure_callback(self, event):

		### check if container is bigger than canvas
		if self.winfo_width() < int(self.canvas['width']):
			self.hscroll_state(ON)
		else:
			self.hscroll_state(OFF)

		if self.winfo_height() < int(self.canvas['height']):
			self.vscroll_state(ON)
		else:
			self.vscroll_state(OFF)

	def getdata(self, col_row):
		"""returns data value of the numeric array given the 
		photo image pixel coords"""
		return self.numimage.get_crvalue(col_row)

	def canvasxy_to_imagexy(self, coord):
		"""
		Return the image coords given the canvas coords.
		Normally (0,0) of image is anchored to (0,0) of canvas
		so there is a direct mapping of canvas to image coords
		"""
		### If anchoring image other than NW->(0,0), 
		### this should become more complicated
		return coord

	def extrema(self):
		if self.numimage is not None:
			return self.numimage.extrema
		else:
			return None

	def resize(self, x1, y1, x2, y2):
		newwidth = x2 - x1
		newheight = y2 - y1
		self.canvas['width'] = newwidth
		self.canvas['height'] = newheight
		self.canvas['scrollregion'] = (x1,y1,x2,y2)

	def use_numeric(self, ndata):
		## use the old value of clip
		oldclip = self.clip()
		if ndata is None:
			## should probably clear canvas here
			return
		self.numimage = NumericImage(ndata,clip=oldclip)
		sw = self.scalingwidget
		zw = self.zoomingwidget
		if sw is not None:
			extrema = self.extrema()
			# this should probably not shrink the range
			sw.set_limits(extrema)
			if not sw.scalelock.get():
				sw.set_values(extrema)
		if zw is not None:
			if zw.zoomlock.get():
				self.zoom(zw.get())
			else:
				zw.set(1.0)
				self.zoom(1.0)
		self.update_canvas()

	def clip(self, newclip=None):
		if newclip:
			self.__set_numimage_clip(newclip)
			self.update_canvas()

		return self.__get_numimage_clip()

	def __set_numimage_clip(self, newclip):
		if self.numimage is not None:
			self.numimage.transform['clip'] = newclip

	def __get_numimage_clip(self):
		if self.numimage is not None:
			return self.numimage.transform['clip']
		else:
			return None

	def update_canvas(self):
		if self.numimage is None:
			self.photo = None
		else:
			self.numimage.update_image()
			## this next line is currently the time waster
			self.photo = self.numimage.photoimage()
			newwidth = self.photo.width()
			newheight = self.photo.height()
			self.resize(0,0,newwidth,newheight)
		self.deleteMessage()
		self.canvas.itemconfig(self.canimage, image=self.photo)

	def zoom(self, factor):
		if self.numimage is None:
			return

		oldsize = self.numimage.orig_size
		newsizex = int(round(oldsize[0] * factor))
		newsizey = int(round(oldsize[1] * factor))
		self.numimage.transform['output_size'] = (newsizex, newsizey)

	def canvasx(self, *args, **kargs):
		return self.canvas.canvasx(*args, **kargs)

	def canvasy(self, *args, **kargs):
		return self.canvas.canvasy(*args, **kargs)

	def leave_callback(self, event):
		self.cursorinfo.clear()

	def enter_callback(self, event):
		pass
		#self.canvas['cursor'] = 'crosshair'

	def motion_callback(self, event):
		info = self.eventXYInfo(event)
		self.cursorinfo.set(info)

	def eventXYInfo(self, event):
		info = {
			'canvas x': None,
			'canvas y': None,
			'image x': None,
			'image y': None,
			'array shape': None,
			'array row': None,
			'array column': None,
			'array value': None
		}

		canx = int(self.canvas.canvasx(event.x))
		cany = int(self.canvas.canvasy(event.y))
		if (not (0 <= canx < self.canvas['width'])) or (not (0 <= cany < self.canvas['height'])):
			return info

		info['canvas x'] = canx
		info['canvas y'] = cany
		imx,imy = self.canvasxy_to_imagexy( (canx, cany) )
		info['image x'] = imx
		info['image y'] = imy
		if self.numimage is None:
			return info
		numrc = self.numimage.imagexy_to_numericrc( (imx, imy) )
		if numrc is None:
			return info
		info['array shape'] =  self.numimage.orig_array.shape
		info['array row'] =  numrc[0]
		info['array column'] =  numrc[1]
		info['array value'] = self.getdata((numrc[1],numrc[0]))

		return info

	def cursorinfo_widget(self, parent, *args, **kargs):
		return self.cursorinfo.widget(parent, bg=self['bg'], *args, **kargs)

	def scaling_widget(self, parent, *args, **kwargs):
		wid = ScalingWidget(parent, self, bg=self['bg'], *args, **kwargs)
		self.scalingwidget = wid
		return wid

	def zooming_widget(self, parent, *args, **kwargs):
		wid = ZoomingWidget(parent, self, bg=self['bg'], *args, **kwargs)
		self.zoomingwidget = wid
		return wid


class CursorInfo:
	"""
	CursorInfo(imagecanvas)
	Maintains info about what is under the cursor.
	"""
	def __init__(self, imagecanvas):
		self.imagecanvas = imagecanvas
		self.numx = IntVar()
		self.numy = IntVar()
		self.numdata = DoubleVar()
		self.imagelevel = IntVar()

	def clear(self):
		self.numx.set('')
		self.numy.set('')
		self.numdata.set('')

	def set(self, xyinfo):
		imcan = self.imagecanvas
		if xyinfo['array column'] is not None:
			self.numx.set(xyinfo['array column'])
		else:
			self.numx.set('')
		if xyinfo['array row'] is not None:
			self.numy.set(xyinfo['array row'])
		else:
			self.numy.set('')

		if xyinfo['array value'] is not None:
			numdata = xyinfo['array value']
			self.numdata.set('%.4f' % numdata)
		else:
			self.numy.set('')

	def widget(self, parent, *args, **kargs):
		return CursorInfoWidget(parent, self, *args, **kargs)
		
class CursorInfoWidget(Frame):
	def __init__(self, parent, cursorinfo, *args, **kargs):
		Frame.__init__(self,parent, *args, **kargs)
		self.xlab = Label(self, textvariable=cursorinfo.numx, width=6)
		self.ylab = Label(self, textvariable=cursorinfo.numy, width=6)
		self.ilab = Label(self, textvariable=cursorinfo.numdata, width=9)
		self.xlab['bg'] = self['bg']
		self.ylab['bg'] = self['bg']
		self.ilab['bg'] = self['bg']
		self.xlab.pack(side=LEFT)
		self.ylab.pack(side=LEFT)
		self.ilab.pack(side=LEFT)

class ZoomingWidget(Frame):
	def __init__(self, parent, imagecanvas, *args, **kargs):
		Frame.__init__(self, parent, *args, **kargs)
		self.imagecanvas = imagecanvas
		self.factor = 1.0
		self.__build()

	def __build(self):
		Button(self, text='Zoom In', command=self.zoomin, bg=self['bg']).pack(side=LEFT)
		Button(self, text='Zoom Out', command=self.zoomout, bg=self['bg']).pack(side=LEFT)
		self.zoomlock = BooleanVar()
		Checkbutton(self, text='Lock', variable=self.zoomlock, bg=self['bg']).pack(side=LEFT)

	def zoomin(self):
		self.factor = self.factor * 2.0
		self.imagecanvas.zoom(self.factor)
		self.imagecanvas.update_canvas()

	def zoomout(self):
		self.factor = self.factor * 0.5
		self.imagecanvas.zoom(self.factor)
		self.imagecanvas.update_canvas()

	def set(self, value):
		self.factor = value

	def get(self):
		return self.factor

class ScalingWidget(Frame):
	def __init__(self, parent, imagecanvas, *args, **kargs):
		Frame.__init__(self, parent, *args, **kargs)
		self.imagecanvas = imagecanvas
		self.rangemin = DoubleVar()
		self.rangemax = DoubleVar()
		self.limit_from = None
		self.limit_to = None
		self.minscalevalue = None
		self.maxscalevalue = None
		self.scalewidth = 300
		self.gradheight = 10
		self.__build()
		self.__callbacks_on()

	def __build(self):
		scaleframe = Frame(self)
		self.minscale = Scale(scaleframe, orient=HORIZONTAL, showvalue=NO, width=8, length=self.scalewidth, troughcolor=self['bg'], bg='black', activebackground='black', bd=0)
		self.maxscale = Scale(scaleframe, orient=HORIZONTAL, showvalue=NO, width=8, length=self.scalewidth, troughcolor=self['bg'], bg='white', activebackground='white', bd=0)
		self.gradcanvas = Canvas(scaleframe, width=self.scalewidth, height=self.gradheight)
		self.gradcanimage = self.gradcanvas.create_image(0,0,anchor=NW)
		self.newGradient()

		self.minscale.pack(side=TOP)
		self.gradcanvas.pack(side=TOP)
		self.maxscale.pack(side=TOP)

		labframe = Frame(self, bg=self['bg'])
		self.minlab = Label(labframe, textvariable=self.rangemin, width=7, bg=self['bg'])
		self.maxlab = Label(labframe, textvariable=self.rangemax, width=7, bg=self['bg'])
		self.scalelock = BooleanVar()
		lockbut = Checkbutton(labframe, text='Lock', variable=self.scalelock, bg=self['bg'])

		self.minlab.grid(column=0, row=0)
		self.maxlab.grid(column=0, row=1)
		lockbut.grid(column=1, row=0, rowspan=2)

		scaleframe.pack(side=LEFT)
		labframe.pack(side=LEFT)

	def gradfunc(self, row, col):
		return self.gradmin + self.gradslope * col

	def newGradient(self):
		newmin = float(self.minscale['from'])
		newmax = float(self.minscale['to'])
		self.gradmin = newmin
		self.gradslope = (newmax - newmin) / self.scalewidth
		image = Numeric.fromfunction(self.gradfunc, (self.gradheight,self.scalewidth))
		self.gradimage = NumericImage(image)

	def updateGradient(self, clip):
		self.gradimage.transform['clip'] = clip
		self.gradimage.update_image()
		self.gradphoto = self.gradimage.photoimage()
		self.gradcanvas.itemconfig(self.gradcanimage, image=self.gradphoto)

	def set_limits(self, newlimits):
		self.limits = newlimits
		newmin = newlimits[0]
		newmax = newlimits[1]
		newres = (newmax - newmin) / 256.0
		self.minscale['resolution'] = newres
		self.maxscale['resolution'] = newres
		self.minscale['from'] = newmin
		self.maxscale['from'] = newmin
		self.minscale['to'] = newmax
		self.maxscale['to'] = newmax
		self.newGradient()

	def set_values(self, newvalues):
		self.minscale.set(newvalues[0])
		self.maxscale.set(newvalues[1])
		self.updateGradient(newvalues)

	def __callbacks_on(self):
		self.minscale['command'] = self._minscale_callback
		self.maxscale['command'] = self._maxscale_callback

	def __callbacks_off(self):
		self.minscale['command'] = None
		self.maxscale['command'] = None

	def _minscale_callback(self, newval=None):
		### turn off this callback while it is running
		self.minscale['command'] = ''
		#self.__callbacks_off()
		if self.minscalevalue == newval:
			self.minscale['command'] = self._minscale_callback
			#self.__callbacks_on()
			return
		self.minscalevalue = newval
		self.rangemin.set(newval)
		self.__update_imagecanvas()
		self.minscale['command'] = self._minscale_callback
		#self.__callbacks_on()

	def _maxscale_callback(self, newval=None):
		### turn off this callback while it is running
		self.maxscale['command'] = ''
		if self.maxscalevalue == newval:
			self.maxscale['command'] = self._maxscale_callback
			return
		self.maxscalevalue = newval
		self.rangemax.set(newval)
		self.__update_imagecanvas()
		self.maxscale['command'] = self._maxscale_callback

	def __update_imagecanvas(self):
		"""update the clipping on the imageitem"""
		rangemin = self.minscale.get()
		rangemax = self.maxscale.get()
		newrange = (rangemin, rangemax)
		self.imagecanvas.clip(newrange)
		self.updateGradient(newrange)

if __name__ == '__main__':
	mycan = ImageCanvas(None,bg='darkgrey')
	mycan.pack(expand=YES,fill=BOTH)

	from mrc.Mrc import *
	ndata = mrc_to_numeric('float.mrc')
	mycan.use_numeric(ndata)
	mycan.update_canvas()

	newwin = Toplevel()
	sw = ScalingWidget(newwin)
	sw.pack()

	sw.add_imagecanvas(mycan)

	mycan.mainloop()
