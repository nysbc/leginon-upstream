import sys
import logging
import wx
from wx.lib.mixins.listctrl import ColumnSorterMixin
import gui.wx.MessageLog

class LoggingConfiguration(object):
	def __init__(self):
		pass

	def _getLevel(self, logger):
		level = logger.level
		if type(level) is not str:
			level = logging.getLevelName(level)
		return level

	def _getLevelNames(self):
		levelnames = []
		for i in logging._levelNames:
			if type(i) is int:
				levelnames.append(i)
		levelnames.sort()
		levelnames = map(lambda n: logging._levelNames[n], levelnames)
		return levelnames

	def _getLoggerNames(self):
		# not accurate, but you can't delete loggers...
		# ideally you'd want two locks in logging
		logging._acquireLock()
		try:
			names = logging.root.manager.loggerDict.keys()
		finally:
			logging._releaseLock()
		names.sort()
		return names

	def _testHandler(self, logger):
		handler = logging.StreamHandler()
		formatter = logging.Formatter()
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		logger.setLevel(logging.INFO)
		logger.info('Hello?')

'''
class Dialog(wx.Dialog):
	def __init__(self, parent, title):
		wx.Dialog.__init__(self, parent, -1, title)

		sz = wx.GridBagSizer(5, 5)

		szbuttons = wx.GridBagSizer(5, 5)
		szbuttons.AddGrowableCol(0)

		sbsz = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Handler'), wx.VERTICAL)
		sbsz.Add(sz, 1, wx.EXPAND|wx.ALL, 5)

		szdialog = wx.GridBagSizer(5, 5)
		szdialog.Add(sbsz, (0, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		szdialog.Add(szbuttons, (1, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		szdialog.AddGrowableRow(0)
		szdialog.AddGrowableCol(0)

		self.SetSizerAndFit(szdialog)
'''

class EditHandlerDialog(wx.Dialog):
	def __init__(self, parent, handler=None, window=None):
		if handler is None:
			title = 'Add Handler'
		else:
			title = 'Edit Handler'
		wx.Dialog.__init__(self, parent, -1, title)

		self.handler = handler
		self.window = window

		if handler is None:
			handlertypes = [logging.StreamHandler]
			if window is not None:
				handlertypes.append(MessageLogHandler)
			self.handlertypes = {}
			for ht in handlertypes:
				self.handlertypes[ht.__name__] = ht
			self.ctype = wx.Choice(self, -1, choices=self.handlertypes.keys())
			self.ctype.SetSelection(0)
		else:
			self.ctype = wx.StaticText(self, -1, handler.__class__.__name__)

		if handler is None:
			format = ''
			dateformat = ''
		else:
			format = handler.formatter._fmt
			if format is None:
				format = ''
			dateformat = handler.formatter.datefmt
			if dateformat is None:
				dateformat = ''
		self.tcformat = wx.TextCtrl(self, -1, format)
		self.tcdateformat = wx.TextCtrl(self, -1, dateformat)

		sz = wx.GridBagSizer(5, 5)
		label = wx.StaticText(self, -1, 'Type:')
		sz.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.ctype, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		label = wx.StaticText(self, -1, 'Format:')
		sz.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.tcformat, (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
		label = wx.StaticText(self, -1, 'Date format:')
		sz.Add(label, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.tcdateformat, (2, 1), (1, 1),
						wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
		sz.AddGrowableCol(1)

		szbuttons = wx.GridBagSizer(5, 5)
		self.bok = wx.Button(self, wx.ID_OK, 'OK')
		self.bcancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		szbuttons.Add(self.bok, (0, 0), (1, 1),
									wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
		szbuttons.Add(self.bcancel, (0, 1), (1, 1), wx.ALIGN_CENTER)
		szbuttons.AddGrowableCol(0)

		sbsz = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Handler'), wx.VERTICAL)
		sbsz.Add(sz, 1, wx.EXPAND|wx.ALL, 5)

		szdialog = wx.GridBagSizer(5, 5)
		szdialog.Add(sbsz, (0, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		szdialog.Add(szbuttons, (1, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		szdialog.AddGrowableRow(0)
		szdialog.AddGrowableCol(0)

		self.SetSizerAndFit(szdialog)

	def getValues(self):
		if isinstance(self.ctype, wx.Choice):
			handlertype = self.handlertypes[self.ctype.GetStringSelection()]
			if issubclass(handlertype, logging.StreamHandler):
				args = ()
			elif issubclass(handlertype, MessageLogHandler):
				args = (self.window,)
			else:
				raise RuntimeError('Unknown handler type')
			handler = handlertype(*args)
		else:
			handler = self.handler

		format = self.tcformat.GetValue()
		if not format:
			format = None
		dateformat = self.tcdateformat.GetValue()
		if not dateformat:
			dateformat = None
		return handler, format, dateformat

class HandlersListCtrl(wx.ListCtrl, ColumnSorterMixin):
	def __init__(self, parent):
		wx.ListCtrl.__init__(self, parent, -1, style=wx.LC_REPORT|wx.LC_SINGLE_SEL)
		self.InsertColumn(0, 'Type')
		self.InsertColumn(1, 'Format')
		self.InsertColumn(2, 'Date Format')

		self.data = 0
		self.itemDataMap = {}
		ColumnSorterMixin.__init__(self, 3)

		self.handlers = {}

	def GetListCtrl(self):
		return self

	def addHandler(self, handler):
		handlertype = handler.__class__.__name__
		format = handler.formatter._fmt
		dateformat = str(handler.formatter.datefmt)
		index = self.InsertStringItem(0, handlertype)
		self.SetStringItem(index, 1, format)
		self.SetStringItem(index, 2, dateformat)
		self.SetItemData(index, self.data)
		self.itemDataMap[self.data] = (handlertype, format, dateformat)
		self.handlers[handler] = self.data
		self.data += 1

	def updateHandler(self, handler):
		data = self.handlers[handler]
		index = self.FindItemData(-1, data)
		format = handler.formatter._fmt
		dateformat = str(handler.formatter.datefmt)
		self.SetStringItem(index, 1, format)
		self.SetStringItem(index, 2, dateformat)

	def removeHandler(self, handler):
		data = self.handlers[handler]
		del self.handlers[handler]
		del self.itemDataMap[data]
		index = self.FindItemData(-1, data)
		self.DeleteItem(index)

	def getSelectedHandler(self):
		for handler, data in self.handlers.items():
			index = self.FindItemData(-1, data)
			if self.GetItemState(index, wx.LIST_STATE_SELECTED):
				return handler

class HandlersPanel(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent, -1)

		self.logger = None

		self.handlers = HandlersListCtrl(self)

		self.badd = wx.Button(self, -1, 'Add...')
		self.bedit = wx.Button(self, -1, 'Edit...')
		self.bedit.Enable(False)
		self.bremove = wx.Button(self, -1, 'Remove')
		self.bremove.Enable(False)

		sz = wx.GridBagSizer(5, 5)
		sz.Add(self.handlers, (0, 0), (4, 1), wx.EXPAND)
		sz.Add(self.badd, (0, 1), (1, 1), wx.ALIGN_CENTER)
		sz.Add(self.bedit, (1, 1), (1, 1), wx.ALIGN_CENTER)
		sz.Add(self.bremove, (2, 1), (1, 1), wx.ALIGN_CENTER)
		sz.AddGrowableCol(0)
		sz.AddGrowableRow(3)

		sbsz = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Handlers'), wx.VERTICAL)
		sbsz.Add(sz, 1, wx.EXPAND|wx.ALL, 5)

		self.SetSizerAndFit(sbsz)

		self.Bind(wx.EVT_BUTTON, self.onAddButton, self.badd)
		self.Bind(wx.EVT_BUTTON, self.onEditButton, self.bedit)
		self.Bind(wx.EVT_BUTTON, self.onRemoveButton, self.bremove)

		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onHandlerSelected, self.handlers)
		self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onHandlerDeselected,
							self.handlers)

	def onHandlerSelected(self, evt):
		self.bedit.Enable(True)
		self.bremove.Enable(True)

	def onHandlerDeselected(self, evt):
		self.bedit.Enable(False)
		self.bremove.Enable(False)

	def setLogger(self, logger):
		self.handlers.DeleteAllItems()
		if logger is None:
			return
		for handler in logger.handlers:
			self.handlers.addHandler(handler)
		self.logger = logger
		self.bedit.Enable(False)
		self.bremove.Enable(False)

	def onAddButton(self, evt):
		if hasattr(self.logger, 'window'):
			window = self.logger.window
		else:
			window = None
		dialog = EditHandlerDialog(self, window=window)
		if dialog.ShowModal() == wx.ID_OK:
			handler, format, dateformat = dialog.getValues()
			formatter = logging.Formatter(format, dateformat)
			handler.setFormatter(formatter)
			self.logger.addHandler(handler)
			self.handlers.addHandler(handler)
		dialog.Destroy()

	def onEditButton(self, evt):
		handler = self.handlers.getSelectedHandler()
		dialog = EditHandlerDialog(self, handler)
		if dialog.ShowModal() == wx.ID_OK:
			handler, format, dateformat = dialog.getValues()
			formatter = logging.Formatter(format, dateformat)
			handler.setFormatter(formatter)
			self.handlers.updateHandler(handler)
		dialog.Destroy()

	def onRemoveButton(self, evt):
		handler = self.handlers.getSelectedHandler()
		self.logger.removeHandler(handler)
		self.handlers.removeHandler(handler)

class LoggingConfigurationDialog(wx.Dialog, LoggingConfiguration):
	def __init__(self, parent):
		style = wx.DEFAULT_DIALOG_STYLE
		style |= wx.MAXIMIZE_BOX
		style |= wx.MINIMIZE_BOX
		style |= wx.RESIZE_BORDER
		wx.Dialog.__init__(self, parent, -1, 'Logging Configuration', style=style)
		LoggingConfiguration.__init__(self)

		self.tree = wx.TreeCtrl(self, -1)

		self.cbpropagate = wx.CheckBox(self, -1, 'Propagate')

		self.clevel = wx.Choice(self, -1, choices=self._getLevelNames())
		self.clevel.SetSelection(0)

		self.handlerspanel = HandlersPanel(self)

		self.btest = wx.Button(self, -1, 'Test')

		donebutton = wx.Button(self, wx.ID_OK, 'Done')
		donebutton.SetDefault()
		buttonsizer = wx.GridBagSizer(0, 0)
		buttonsizer.Add(donebutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
		buttonsizer.AddGrowableCol(0)

		sizer = wx.GridBagSizer(5, 5)
		sizer.Add(self.tree, (0, 0), (4, 1), wx.EXPAND)
		sizer.SetItemMinSize(self.tree, (self.tree.GetSize()[0]*2, -1))
		sizer.Add(self.cbpropagate, (0, 1), (1, 2), wx.ALIGN_CENTER_VERTICAL)
		label = wx.StaticText(self, -1, 'Level:')
		sizer.Add(label, (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.clevel, (1, 2), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.handlerspanel, (2, 1), (1, 2), wx.EXPAND)
		sizer.Add(self.btest, (3, 1), (1, 2), wx.ALIGN_CENTER)
		sizer.Add(buttonsizer, (4, 1), (1, 3), wx.EXPAND)
		sizer.AddGrowableRow(2)
		sizer.AddGrowableCol(0)
		sizer.AddGrowableCol(1)

		self.setTree()
		self.onTreeSelectionChanged()

		self.Bind(wx.EVT_CHECKBOX, self.onPropagateCheckbox, self.cbpropagate)
		self.Bind(wx.EVT_CHOICE, self.onLevelChoice, self.clevel)
		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSelectionChanged, self.tree)
		self.Bind(wx.EVT_BUTTON, self.onTestButton, self.btest)

		self.dialogsizer = wx.GridBagSizer(5, 5)
		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		self.dialogsizer.AddGrowableRow(0)
		self.dialogsizer.AddGrowableCol(0)
		self.SetSizerAndFit(self.dialogsizer)

	def onTestButton(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		logger.info('This a test, it is only a test.')

	def onPropagateCheckbox(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		logger.propagate = evt.IsChecked()

	def onLevelChoice(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		logger.setLevel(logging._levelNames[evt.GetString()])

	def onTreeSelectionChanged(self, evt=None):
		if evt is None:
			logger = self.tree.GetPyData(self.tree.GetSelection())
		else:
			logger = self.tree.GetPyData(evt.GetItem())

		self.cbpropagate.SetValue(logger.propagate)

		level = self._getLevel(logger)
		if type(level) is not str:
			level = logging.getLevelName(level)
		self.clevel.SetStringSelection(level)

		self.handlerspanel.setLogger(logger)

	def expandAll(self, item):
		self.tree.Expand(item)
		child, cookie = self.tree.GetFirstChild(item)
		while child:
			self.expandAll(child)
			child, cookie = self.tree.GetNextChild(child, cookie)

	def setTree(self):
		self.root = self.tree.AddRoot('Root')
		self.tree.SetPyData(self.root, logging.root)
		for loggername in self._getLoggerNames():
			names = loggername.split('.')
			parent = self.root
			for name in names[:-1]:
				child, cookie = self.tree.GetFirstChild(parent)
				while self.tree.GetItemText(child) != name:
					child, cookie = self.tree.GetNextChild(child, cookie)
				parent = child
			child = self.tree.AppendItem(parent, names[-1])
			self.tree.SetPyData(child, logging.getLogger(loggername))
		self.expandAll(self.root)
		self.tree.SelectItem(self.root)
		self.tree.EnsureVisible(self.root)

class MessageLogHandler(logging.Handler):
	def __init__(self, window, level=logging.NOTSET):
		self.window = window
		self.levels = {
			'ERROR': 'error',
			'WARNING': 'warning',
			'INFO': 'info',
		}
		logging.Handler.__init__(self, level)

	def getLevel(self, record):
		try:
			return self.levels[record.levelname]
		except KeyError:
			return None

	def emit(self, record):
		level = self.getLevel(record)
		if level is None:
			return
		message = record.getMessage()
		evt = gui.wx.MessageLog.AddMessageEvent(self.window, level, message)
		self.window.GetEventHandler().AddPendingEvent(evt)

if __name__ == '__main__':
	class App(wx.App):
		def OnInit(self):

			l = logging.getLogger('Test')
			h = logging.StreamHandler()
			f = logging.Formatter()
			h.setFormatter(f)
			l.addHandler(h)
			l.setLevel(logging.INFO)
			l.info('Initialized...')

			frame = wx.Frame(None, -1, 'Message Log Test')

			panel = wx.Panel(frame, -1)

			dialog = LoggingConfigurationDialog(panel)
			dialog.Show()

			sizer = wx.GridBagSizer(5, 5)
			sizer.AddGrowableRow(0)
			sizer.AddGrowableCol(0)

			panel.SetSizerAndFit(sizer)

			frame.Fit()
			self.SetTopWindow(frame)
			frame.Show()
			return True

	app = App(0)
	app.MainLoop()

