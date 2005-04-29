import wx
import numarrayimage
import numextension

class	Panel(wx.Window):
	def __init__(self, parent, id):
		wx.Window.__init__(self, parent, id)

		self.ignoresize = False

		clientwidth, clientheight = self.GetClientSize()
		self.buffer = wx.EmptyBitmap(clientwidth, clientheight)

		self.validregion = None

		self.source = None
		self.extrema = None

		self.scaledwidth = None
		self.scaledheight = None

		self.Bind(wx.EVT_ERASE_BACKGROUND, self.onEraseBackground)
		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_SCROLLWIN_TOP, self.onScrollWinTop)
		self.Bind(wx.EVT_SCROLLWIN_BOTTOM, self.onScrollWinBottom)
		self.Bind(wx.EVT_SCROLLWIN_LINEUP, self.onScrollWinLineUp)
		self.Bind(wx.EVT_SCROLLWIN_LINEDOWN, self.onScrollWinLineDown)
		self.Bind(wx.EVT_SCROLLWIN_PAGEUP, self.onScrollWinPageUp)
		self.Bind(wx.EVT_SCROLLWIN_PAGEDOWN, self.onScrollWinPageDown)
		self.Bind(wx.EVT_SCROLLWIN_THUMBTRACK, self.onScrollWinThumbTrack)

	def copyBuffer(self, dc, region, offset):
		xoffset, yoffset = offset
		regioniterator = wx.RegionIterator(region)
		copydc = wx.MemoryDC()
		copydc.SelectObject(self.buffer)
		while(regioniterator):
			r = regioniterator.GetRect()
			dc.Blit(r.x, r.y, r.width, r.height, copydc, r.x + xoffset, r.y + yoffset)
			regioniterator.Next()
		copydc.SelectObject(wx.NullBitmap)

	def sourceBuffer(self, dc, region, offset):
		xoffset, yoffset = offset
		regioniterator = wx.RegionIterator(region)
		while(regioniterator):
			r = regioniterator.GetRect()
			bitmap = numarrayimage.numarray2wxBitmap(array,
																					r.x + xoffset, r.y + yoffset,
																					r.width, r.height,
																					self.scaledwidth, self.scaledheight,
																					self.extrema)
			sourcedc = wx.MemoryDC()
			sourcedc.SelectObject(bitmap)
			dc.Blit(r.x, r.y, r.width, r.height, sourcedc, 0, 0)
			sourcedc.SelectObject(wx.NullBitmap)
			regioniterator.Next()

	def onScroll(self, x, y):
		clientwidth, clientheight = self.GetClientSize()
		clientregion = wx.Region(0, 0, clientwidth, clientheight)

		if self.scaledwidth > clientwidth:
			dx = x - self.GetScrollPos(wx.HORIZONTAL)
			bitmapx = -x
		else:
			dx = 0
			bitmapx = int(round((clientwidth - self.scaledwidth)/2.0))

		if self.scaledheight > clientheight:
			dy = y - self.GetScrollPos(wx.VERTICAL)
			bitmapy = -y
		else:
			dy = 0
			bitmapy = int(round((clientheight - self.scaledheight)/2.0))

		bitmapregion = wx.Region(bitmapx, bitmapy,
															self.scaledwidth, self.scaledheight)

		self.validregion.Offset(-dx, -dy)

		copyregion = wx.Region()
		copyregion.UnionRegion(clientregion)
		copyregion.IntersectRegion(self.validregion)

		sourceregion = wx.Region()
		sourceregion.UnionRegion(clientregion)
		sourceregion.IntersectRegion(bitmapregion)
		sourceregion.SubtractRegion(copyregion)

		buffer = wx.EmptyBitmap(clientwidth, clientheight)

		dc = wx.MemoryDC()
		dc.SelectObject(buffer)
		dc.Clear()
		self.copyBuffer(dc, copyregion, (dx, dy))
		self.sourceBuffer(dc, sourceregion, (-bitmapx, -bitmapy))
		dc.SelectObject(wx.NullBitmap)

		self.validregion = wx.Region()
		self.validregion.UnionRegion(copyregion)
		self.validregion.UnionRegion(sourceregion)

		self.buffer = buffer

		self.SetScrollPos(wx.HORIZONTAL, x)
		self.SetScrollPos(wx.VERTICAL, y)

		self.Refresh()

	def onScrollWin(self, orientation, position):
		if orientation == wx.HORIZONTAL:
			x = position
			x = max(0, x)
			x = min(x, self.GetScrollRange(orientation)
									- self.GetScrollThumb(orientation))
			y = self.GetScrollPos(wx.VERTICAL)
		elif orientation == wx.VERTICAL:
			x = self.GetScrollPos(wx.HORIZONTAL)
			y = position
			y = max(0, y)
			y = min(y, self.GetScrollRange(orientation)
									- self.GetScrollThumb(orientation))
		self.onScroll(x, y)

	def onScrollWinTop(self, evt):
		orientation = evt.GetOrientation()
		position = 0
		self.onScrollWin(orientation, position)

	def onScrollWinBottom(self, evt):
		orientation = evt.GetOrientation()
		position = self.GetScrollRange(orientation)
		position -= self.GetScrollThumb(orientation)
		self.onScrollWin(orientation, position)

	def onScrollWinLineUp(self, evt):
		orientation = evt.GetOrientation()
		position = self.GetScrollPos(orientation)
		position -= 1
		self.onScrollWin(orientation, position)

	def onScrollWinLineDown(self, evt):
		orientation = evt.GetOrientation()
		position = self.GetScrollPos(orientation)
		position += 1
		self.onScrollWin(orientation, position)

	def onScrollWinPageUp(self, evt):
		orientation = evt.GetOrientation()
		position = self.GetScrollPos(orientation)
		position -= self.GetScrollThumb(orientation)
		self.onScrollWin(orientation, position)

	def onScrollWinPageDown(self, evt):
		orientation = evt.GetOrientation()
		position = self.GetScrollPos(orientation)
		position += self.GetScrollThumb(orientation)
		self.onScrollWin(orientation, position)

	def onScrollWinThumbTrack(self, evt):
		orientation = evt.GetOrientation()
		position = evt.GetPosition()
		self.onScrollWin(orientation, position)

	def setNumarray(self, array):
		self.source = array

		if self.source is None:
			self.extrema = None
			dc = wx.MemoryDC()
			dc.SelectObject(self.buffer)
			dc.Clear()
			dc.SelectObject(wx.NullBitmap)
			self.Refresh()
			return

		self.extrema = numextension.minmax(self.source)

		clientwidth, clientheight = self.GetClientSize()
		clientregion = wx.Region(0, 0, clientwidth, clientheight)

		self.scaledwidth = self.source.shape[1]
		self.scaledheight = self.source.shape[0]
		bitmapx = max(0, int(round((clientwidth - self.scaledwidth)/2.0)))
		bitmapy = max(0, int(round((clientheight - self.scaledheight)/2.0)))
		bitmapregion = wx.Region(bitmapx, bitmapy,
															self.scaledwidth, self.scaledheight)

		sourceregion = wx.Region()
		sourceregion.UnionRegion(clientregion)
		sourceregion.IntersectRegion(bitmapregion)

		dc = wx.MemoryDC()
		dc.SelectObject(self.buffer)
		dc.Clear()
		self.sourceBuffer(dc, sourceregion, (-bitmapx, -bitmapy))
		dc.SelectObject(wx.NullBitmap)

		self.validregion = sourceregion

		self.Refresh()

	def onEraseBackground(self, evt):
		pass

	def onPaint(self, dc):
		dc = wx.PaintDC(self) 
		memorydc = wx.MemoryDC()
		memorydc.SelectObject(self.buffer)
		regioniterator = wx.RegionIterator(self.GetUpdateRegion())
		while(regioniterator):
			r = regioniterator.GetRect()
			dc.Blit(r.x, r.y, r.width, r.height, memorydc, r.x, r.y)
			regioniterator.Next()
		memorydc.SelectObject(wx.NullBitmap)

	def onSize(self, evt):
		if self.ignoresize:
			evt.Skip()
			return

		width, height = self.GetSize()

		if self.source is None or width < 1 or height < 1:
			self.ignoresize = True
			self.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)
			self.SetScrollbar(wx.VERTICAL, 0, 0, 0)
			self.ignoresize = False
			self.buffer = wx.EmptyBitmap(width, height)
			dc = wx.MemoryDC()
			dc.SelectObject(self.buffer)
			dc.Clear()
			dc.SelectObject(wx.NullBitmap)
			return

		# region of the bitmap relative to the client

		self.ignoresize = True

		bufferwidth = self.buffer.GetWidth()
		if self.scaledwidth < bufferwidth:
			x = int(round((bufferwidth - self.scaledwidth)/2.0))
		else:
			x = -self.GetScrollPos(wx.HORIZONTAL)

		bufferheight = self.buffer.GetHeight()
		if self.scaledheight < bufferheight:
			y = int(round((bufferheight - self.scaledheight)/2.0))
		else:
			y = -self.GetScrollPos(wx.VERTICAL)

		if self.scaledwidth > width:
			scrollx = self.GetScrollPos(wx.HORIZONTAL)
			self.SetScrollbar(wx.HORIZONTAL, scrollx, width, self.scaledwidth, False)
		else:
			self.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)

		clientwidth, clientheight = self.GetClientSize()

		if self.scaledheight > clientheight:
			scrolly = max(0, -y)
			scrolly = min(scrolly, self.scaledheight - clientheight)
			bitmapy = -scrolly
			self.SetScrollbar(wx.VERTICAL, scrolly, clientheight, self.scaledheight)
		else:
			bitmapy = int(round((clientheight - self.scaledheight)/2.0))
			self.SetScrollbar(wx.VERTICAL, 0, 0, 0)
		dy = y - bitmapy

		clientwidth, clientheight = self.GetClientSize()

		if self.scaledwidth > clientwidth:
			scrollx = max(0, -x)
			scrollx = min(scrollx, self.scaledwidth - clientwidth)
			bitmapx = -scrollx
			self.SetScrollbar(wx.HORIZONTAL, scrollx, clientwidth, self.scaledwidth)
		else:
			bitmapx = int(round((clientwidth - self.scaledwidth)/2.0))
			self.SetScrollbar(wx.HORIZONTAL, 0, 0, 0)
		dx = x - bitmapx

		self.ignoresize = False

		self.validregion.Offset(-dx, -dy)

		clientregion = wx.Region(0, 0, clientwidth, clientheight)
		bitmapregion = wx.Region(bitmapx, bitmapy,
															self.scaledwidth, self.scaledheight)

		copyregion = wx.Region()
		copyregion.UnionRegion(clientregion)
		copyregion.IntersectRegion(self.validregion)

		sourceregion = wx.Region()
		sourceregion.UnionRegion(clientregion)
		sourceregion.IntersectRegion(bitmapregion)
		sourceregion.SubtractRegion(copyregion)

		buffer = wx.EmptyBitmap(clientwidth, clientheight)

		dc = wx.MemoryDC()
		dc.SelectObject(buffer)
		dc.Clear()
		self.copyBuffer(dc, copyregion, (dx, dy))
		self.sourceBuffer(dc, sourceregion, (-bitmapx, -bitmapy))
		dc.SelectObject(wx.NullBitmap)

		self.validregion = wx.Region()
		self.validregion.UnionRegion(copyregion)
		self.validregion.UnionRegion(sourceregion)

		self.buffer = buffer

		# if the offset has changed paint the entire panel
		if dx != 0 or dy != 0:
			self.Refresh()

		evt.Skip()

if __name__ == '__main__':
	import sys
	import Mrc

	filename = sys.argv[1]

	class MyApp(wx.App):
		def OnInit(self):
			frame = wx.Frame(None, -1, 'Image Viewer')
			self.sizer = wx.BoxSizer(wx.VERTICAL)

			self.panel = Panel(frame, -1)

			self.sizer.Add(self.panel, 1, wx.EXPAND|wx.ALL)
			frame.SetSizerAndFit(self.sizer)
			self.SetTopWindow(frame)
			frame.SetSize((750, 750))
			frame.Show(True)
			return True

	app = MyApp(0)

	array = Mrc.mrcstr_to_numeric(open(filename, 'rb').read())
	app.panel.setNumarray(array)
	app.MainLoop()

