import event
import logging
import manager
import os
import threading
import uiclient
import wx
import wx.lib.intctrl
import gui.wx.Launcher
import gui.wx.Logging

AddNodeEventType = wx.NewEventType()
RemoveNodeEventType = wx.NewEventType()
AddLauncherEventType = wx.NewEventType()
RemoveLauncherEventType = wx.NewEventType()
ApplicationStartingEventType = wx.NewEventType()
ApplicationNodeStartedEventType = wx.NewEventType()
ApplicationStartedEventType = wx.NewEventType()
ApplicationKilledEventType = wx.NewEventType()
AddLauncherPanelEventType = wx.NewEventType()
EVT_ADD_NODE = wx.PyEventBinder(AddNodeEventType)
EVT_REMOVE_NODE = wx.PyEventBinder(RemoveNodeEventType)
EVT_ADD_LAUNCHER = wx.PyEventBinder(AddLauncherEventType)
EVT_REMOVE_LAUNCHER = wx.PyEventBinder(RemoveLauncherEventType)
EVT_APPLICATION_STARTING = wx.PyEventBinder(ApplicationStartingEventType)
EVT_APPLICATION_NODE_STARTED = wx.PyEventBinder(ApplicationNodeStartedEventType)
EVT_APPLICATION_STARTED = wx.PyEventBinder(ApplicationStartedEventType)
EVT_APPLICATION_KILLED = wx.PyEventBinder(ApplicationKilledEventType)
EVT_ADD_LAUNCHER_PANEL = wx.PyEventBinder(AddLauncherPanelEventType)

class AddNodeEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(AddNodeEventType)
		self.name = name

class RemoveNodeEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(RemoveNodeEventType)
		self.name = name

class AddLauncherEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(AddLauncherEventType)
		self.name = name

class RemoveLauncherEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(RemoveLauncherEventType)
		self.name = name

class ApplicationStartingEvent(wx.PyEvent):
	def __init__(self, name, nnodes):
		wx.PyEvent.__init__(self)
		self.SetEventType(ApplicationStartingEventType)
		self.name = name
		self.nnodes = nnodes

class ApplicationNodeStartedEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(ApplicationNodeStartedEventType)
		self.name = name

class ApplicationStartedEvent(wx.PyEvent):
	def __init__(self, name):
		wx.PyEvent.__init__(self)
		self.SetEventType(ApplicationStartedEventType)
		self.name = name

class ApplicationKilledEvent(wx.PyEvent):
	def __init__(self):
		wx.PyEvent.__init__(self)
		self.SetEventType(ApplicationKilledEventType)

class AddLauncherPanelEvent(wx.PyEvent):
	def __init__(self, launcher):
		wx.PyEvent.__init__(self)
		self.SetEventType(AddLauncherPanelEventType)
		self.launcher = launcher

class App(wx.App):
	def __init__(self, session, tcpport=None, xmlrpcport=None, **kwargs):
		self.session = session
		self.tcpport = tcpport
		self.xmlrpcport = xmlrpcport
		self.kwargs = kwargs
		wx.App.__init__(self, 0)

	def OnInit(self):
		self.manager = manager.Manager(self.session, self.tcpport, self.xmlrpcport,
																		**self.kwargs)
		self.SetTopWindow(self.manager.frame)
		self.manager.frame.Show(True)
		return True

	def OnExit(self):
		self.manager.exit()

class StatusBar(wx.StatusBar):
	def __init__(self, parent):
		wx.StatusBar.__init__(self, parent, -1)

class Frame(wx.Frame):
	def __init__(self, manager, research, publish):
		self.manager = manager
		self.research = research
		self.publish = publish
		self.session = None

		wx.Frame.__init__(self, None, -1, 'Leginon', size=(750, 750))

		# menu
		self.menubar = wx.MenuBar()

		# file menu
		filemenu = wx.Menu()
		exit = wx.MenuItem(filemenu, -1, 'E&xit')
		self.Bind(wx.EVT_MENU, self.onExit, exit)
		filemenu.AppendItem(exit)
		self.menubar.Append(filemenu, '&File')

		# application menu
		self.applicationmenu = wx.Menu()
		self.runappmenuitem = wx.MenuItem(self.applicationmenu, -1, '&Run')
		self.killappmenuitem = wx.MenuItem(self.applicationmenu, -1, '&Kill')
		self.importappmenuitem = wx.MenuItem(self.applicationmenu, -1, '&Import')
		self.exportappmenuitem = wx.MenuItem(self.applicationmenu, -1, '&Export')
		self.Bind(wx.EVT_MENU, self.onMenuRunApplication, self.runappmenuitem)
		self.Bind(wx.EVT_MENU, self.onMenuKillApplication, self.killappmenuitem)
		self.Bind(wx.EVT_MENU, self.onMenuImportApplication, self.importappmenuitem)
		self.Bind(wx.EVT_MENU, self.onMenuExportApplication, self.exportappmenuitem)
		self.applicationmenu.AppendItem(self.runappmenuitem)
		self.applicationmenu.AppendItem(self.killappmenuitem)
		self.applicationmenu.AppendSeparator()
		self.applicationmenu.AppendItem(self.importappmenuitem)
		self.applicationmenu.AppendItem(self.exportappmenuitem)
		self.menubar.Append(self.applicationmenu, '&Application')
		self.runappmenuitem.Enable(False)
		self.killappmenuitem.Enable(False)

		# launcher menu
		self.launchermenu = wx.Menu()
		addmenuitem = wx.MenuItem(self.launchermenu, -1, '&Add')
		self.launcherkillmenu = wx.Menu()

		self.Bind(wx.EVT_MENU, self.onMenuAdd, addmenuitem)

		self.launchermenu.AppendItem(addmenuitem)
		self.launcherkillmenuitem = self.launchermenu.AppendMenu(-1, '&Kill',
																											self.launcherkillmenu)

		self.launcherkillmenuitem.Enable(False)

		self.menubar.Append(self.launchermenu, '&Launcher')

		# node menu
		self.nodemenu = wx.Menu()

		self.nodecreatemenuitem = wx.MenuItem(self.nodemenu, -1, '&Create')
		self.nodekillmenu = wx.Menu()

		self.Bind(wx.EVT_MENU, self.onMenuCreate, self.nodecreatemenuitem)

		self.nodemenu.AppendItem(self.nodecreatemenuitem)
		self.nodekillmenuitem = self.nodemenu.AppendMenu(-1, '&Kill',
																											self.nodekillmenu)

		self.nodecreatemenuitem.Enable(False)
		self.nodekillmenuitem.Enable(False)

		self.menubar.Append(self.nodemenu, '&Node')

		# event menu
		self.eventmenu = wx.Menu()
		self.bindmenuitem = wx.MenuItem(self.eventmenu, -1, '&Bind')
		self.Bind(wx.EVT_MENU, self.onMenuBind, self.bindmenuitem)
		self.eventmenu.AppendItem(self.bindmenuitem)
		self.bindmenuitem.Enable(False)
		self.menubar.Append(self.eventmenu, '&Events')

		# settings menu
		self.settingsmenu = wx.Menu()
		self.loggingmenuitem = wx.MenuItem(self.settingsmenu, -1, '&Logging')
		self.Bind(wx.EVT_MENU, self.onMenuLogging, self.loggingmenuitem)
		self.settingsmenu.AppendItem(self.loggingmenuitem)
		self.menubar.Append(self.settingsmenu, '&Settings')

		self.SetMenuBar(self.menubar)

		# status bar
		self.statusbar = StatusBar(self)
		self.SetStatusBar(self.statusbar)

		self.appgauge = None

		self.Bind(EVT_ADD_NODE, self.onAddNode)
		self.Bind(EVT_REMOVE_NODE, self.onRemoveNode)
		self.Bind(EVT_ADD_LAUNCHER, self.onAddLauncher)
		self.Bind(EVT_REMOVE_LAUNCHER, self.onRemoveLauncher)
		self.Bind(EVT_APPLICATION_STARTING, self.onApplicationStarting)
		self.Bind(EVT_APPLICATION_NODE_STARTED, self.onApplicationNodeStarted)
		self.Bind(EVT_APPLICATION_STARTED, self.onApplicationStarted)
		self.Bind(EVT_APPLICATION_KILLED, self.onApplicationKilled)
		self.Bind(EVT_ADD_LAUNCHER_PANEL, self.onAddLauncherPanel)

		self.panel = Panel(self, self.manager.uicontainer.location())

	def onAddLauncherPanel(self, evt):
		# this doesn't really work
		style=wx.CAPTION|wx.SYSTEM_MENU|wx.CLOSE_BOX|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX|wx.RESIZE_BORDER
		dialog = wx.Dialog(self, -1, 'Temporary Launcher Window', style=style)
		#sizer = wx.GridBagSizer(0, 0)
		panel = gui.wx.Launcher.Panel(dialog, evt.launcher)
		#sizer.Add(panel, (0, 0), (1, 1), wx.EXPAND|wx.ALL)
		#dialog.SetSizerAndFit(sizer)

		evt.launcher.panel = panel

		dialog.SetSize((800, 600))
		dialog.Show(True)

	def onExit(self, evt):
		self.manager.exit()
		self.Close()

	def onMenuRunApplication(self, evt):
		apps = self.manager.getApplications()
		launchernames = self.manager.getLauncherNames()
		history = self.manager.getApplicationHistory()
		dialog = RunApplicationDialog(self, apps, launchernames, history)
		if dialog.ShowModal() == wx.ID_OK:
			app = dialog.getValues()
			threading.Thread(name='wx.manager runApplication',
												target=self.manager.runApplication,
												args=(app,)).start()
		dialog.Destroy()

	def onMenuKillApplication(self, evt):
		threading.Thread(name='wx.manager killApplication',
											target=self.manager.killApplication).start()

	def onMenuImportApplication(self, evt):
		dlg = wx.FileDialog(self, message='Select Application File',
												defaultDir=os.getcwd(),
												defaultFile='',
												wildcard='XML file (*.xml)|*.xml|'\
																	'All files (*.*)|*.*',
												style=wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			path = dlg.GetPath()
			self.manager.importApplication(path)
		dlg.Destroy()

	def onMenuExportApplication(self, evt):
		names = self.manager.getApplicationNames()
		dialog = ExportApplicationDialog(self, names)
		if dialog.ShowModal() == wx.ID_OK:
			values = dialog.getValues()
			self.manager.exportApplication(*values)
		dialog.Destroy()

	def onMenuCreate(self, evt):
		launchernames = self.manager.getLauncherNames()
		launcherclasses = self.manager.getLauncherClasses()
		nodenames = self.manager.getNodeNames()
		dialog = CreateNodeDialog(self, launchernames, launcherclasses, nodenames)
		if dialog.ShowModal() == wx.ID_OK:
			values = dialog.getValues()
			self.manager.launchNode(*values)
		dialog.Destroy()

	def onMenuAdd(self, evt):
		dialog = AddNodeDialog(self)
		if dialog.ShowModal() == wx.ID_OK:
			values = dialog.getValues()
			self.manager.addLauncher(*values)
		dialog.Destroy()

	def onMenuKill(self, evt):
		item = self.launcherkillmenu.FindItemById(evt.GetId())
		if item is None:
			item = self.nodekillmenu.FindItemById(evt.GetId())
		name = item.GetLabel()
		self.manager.killNode(name)

	def onMenuBind(self, evt):
		nodenames = self.manager.getNodeNames()
		eventio = {}
		for name in nodenames:
			eventio[name] = self.manager.getNodeEventIO(name)
		eventclasses = event.eventClasses()
		distmap = self.manager.distmap
		dialog = BindEventDialog(self, nodenames, eventio, eventclasses, distmap)
		dialog.ShowModal()
		dialog.Destroy()

	def onMenuLogging(self, evt):
		dialog = gui.wx.Logging.LoggingConfigurationDialog(self)
		dialog.ShowModal()
		dialog.Destroy()

	def onAddNode(self, evt):
		# if it's in launcher kill menu don't add here
		if self.manager.getNodeCount() >= 2:
			self.bindmenuitem.Enable(True)
		item = self.launcherkillmenu.FindItem(evt.name)
		if item is wx.NOT_FOUND:
			item = wx.MenuItem(self.nodekillmenu, -1, evt.name)
			self.nodekillmenu.AppendItem(item)
			self.Bind(wx.EVT_MENU, self.onMenuKill, item)
			if not self.nodekillmenuitem.IsEnabled():
				self.nodekillmenuitem.Enable(True)

	def onRemoveNode(self, evt):
		if self.manager.getNodeCount() < 2:
			self.bindmenuitem.Enable(False)
		item = self.nodekillmenu.FindItem(evt.name)
		if item is not wx.NOT_FOUND:
			self.nodekillmenu.Delete(item)
			if self.nodekillmenu.GetMenuItemCount() < 1:
				self.nodekillmenuitem.Enable(False)

	def onAddLauncher(self, evt):
		if not self.nodecreatemenuitem.IsEnabled():
			self.nodecreatemenuitem.Enable(True)

		if not self.runappmenuitem.IsEnabled():
			if self.manager.application is None:
				self.runappmenuitem.Enable(True)

		item = wx.MenuItem(self.launcherkillmenu, -1, evt.name)
		self.launcherkillmenu.AppendItem(item)
		self.Bind(wx.EVT_MENU, self.onMenuKill, item)
		if not self.launcherkillmenuitem.IsEnabled():
			self.launcherkillmenuitem.Enable(True)

	def onRemoveLauncher(self, evt):
		if self.manager.getLauncherCount() < 1:
			self.nodecreatemenuitem.Enable(False)
			self.runappmenuitem.Enable(False)

		item = self.launcherkillmenu.FindItem(evt.name)
		if item is not wx.NOT_FOUND:
			self.launcherkillmenu.Delete(item)
			if self.launcherkillmenu.GetMenuItemCount() < 1:
				self.launcherkillmenuitem.Enable(False)

	def onApplicationStarting(self, evt):
		self.runappmenuitem.Enable(False)
		count = self.statusbar.GetFieldsCount()
		count += 1
		self.statusbar.SetFieldsCount(count)
		self.statusbar.SetStatusText('Starting application %s...' % evt.name)
		self.appgauge = wx.Gauge(self.statusbar, -1, evt.nnodes)
		self.appgauge.count = 0
		self.applicationGaugeSize()

	def applicationGaugeSize(self, evt=None):
		field = self.statusbar.GetFieldsCount() - 1
		rect = self.statusbar.GetFieldRect(field)
		self.appgauge.SetPosition((rect.x+2, rect.y+2))
		self.appgauge.SetSize((rect.width-4, rect.height-4))

	def onApplicationNodeStarted(self, evt):
		if self.appgauge is not None:
			self.statusbar.SetStatusText('Started %s node' % evt.name)
			self.appgauge.count += 1
			self.appgauge.SetValue(self.appgauge.count)

	def onApplicationStarted(self, evt):
		self.killappmenuitem.Enable(True)
		if self.appgauge is not None:
			self.statusbar.SetStatusText('Application %s started.' % evt.name)
			self.appgauge.Destroy()
			self.appgauge = None
			count = self.statusbar.GetFieldsCount()
			count -= 1
			self.statusbar.SetFieldsCount(count)

	def onApplicationKilled(self, evt):
		self.killappmenuitem.Enable(False)
		if self.manager.getLauncherCount() > 0:
			self.runappmenuitem.Enable(True)

class Panel(wx.ScrolledWindow):
	def __init__(self, parent, location):
		self._enabled = True
		self._shown = True
		wx.ScrolledWindow.__init__(self, parent, -1)
		self.SetScrollRate(5, 5)
		containerclass = uiclient.SimpleContainerWidget
		containerclass = uiclient.ClientContainerFactory(containerclass)
		self.container = containerclass('UI Client', self, self, location, {})
		self.SetSizerAndFit(self.container)

	def layout(self):
		pass

class AddNodeDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, -1, 'Add Node')

		self.dialogsizer = wx.GridBagSizer()

		sizer = wx.GridBagSizer(3, 3)

		sizer.Add(wx.StaticText(self, -1, 'Hostname:'),
							(0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		self.hostnametextctrl = wx.TextCtrl(self, -1, '')
		sizer.Add(self.hostnametextctrl, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		sizer.Add(wx.StaticText(self, -1, 'Port:'),
							(1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		self.portintctrl = wx.lib.intctrl.IntCtrl(self, -1, 55555,
																							min=0, limited=True)
		sizer.Add(self.portintctrl, (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		buttonsizer = wx.GridBagSizer(0, 3)
		addbutton = wx.Button(self, wx.ID_OK, 'Add')
		addbutton.SetDefault()
		buttonsizer.Add(addbutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

		cancelbutton = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		buttonsizer.Add(cancelbutton, (0, 1), (1, 1), wx.ALIGN_CENTER)

		buttonsizer.AddGrowableCol(0)

		sizer.Add(buttonsizer, (2, 0), (1, 2), wx.EXPAND)

		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def getValues(self):
		return self.hostnametextctrl.GetValue(), self.portintctrl.GetValue()

class CreateNodeDialog(wx.Dialog):
	def __init__(self, parent, launchernames, launcherclasses, nodenames):
		self.launchernames = launchernames
		self.launcherclasses = launcherclasses
		self.nodenames = nodenames

		wx.Dialog.__init__(self, parent, -1, 'Create Node')

		self.dialogsizer = wx.GridBagSizer()

		sizer = wx.GridBagSizer(3, 3)
		sizer.Add(wx.StaticText(self, -1, 'Launcher:'), (0, 0), (1, 1),
										wx.ALIGN_CENTER_VERTICAL)

		self.launcherchoice = wx.Choice(self, -1, choices=launchernames)
		self.launcherchoice.SetSelection(0)

		sizer.Add(self.launcherchoice, (0, 1), (1, 1),
										wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		sizer.Add(wx.StaticText(self, -1, 'Type:'), (1, 0), (1, 1),
										wx.ALIGN_CENTER_VERTICAL)

		# size it, then set it
		choices = self.launcherclasses[self.launcherchoice.GetStringSelection()]
		self.typechoice = wx.Choice(self, -1, choices=choices)
		self.typechoice.SetSelection(0)

		self.Bind(wx.EVT_CHOICE, self.onLauncherChoice, self.launcherchoice)

		sizer.Add(self.typechoice, (1, 1), (1, 1),
										wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		sizer.Add(wx.StaticText(self, -1, 'Name:'), (2, 0), (1, 1),
										wx.ALIGN_CENTER_VERTICAL)

		self.nametextctrl = wx.TextCtrl(self, -1, '')
		sizer.Add(self.nametextctrl, (2, 1), (1, 1),
										wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		buttonsizer = wx.GridBagSizer(0, 3)
		createbutton = wx.Button(self, wx.ID_OK, 'Create')
		createbutton.SetDefault()
		buttonsizer.Add(createbutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
		self.Bind(wx.EVT_BUTTON, self.onCreate, createbutton)

		cancelbutton = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		buttonsizer.Add(cancelbutton, (0, 1), (1, 1), wx.ALIGN_CENTER)

		buttonsizer.AddGrowableCol(0)

		sizer.Add(buttonsizer, (4, 0), (1, 2), wx.EXPAND)

		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def onLauncherChoice(self, evt):
		self.Freeze()
		choice = self.typechoice.GetStringSelection()
		self.typechoice.Clear()
		self.typechoice.AppendItems(self.launcherclasses[evt.GetString()])
		selection = self.typechoice.FindString(choice)
		if selection == wx.NOT_FOUND:
			selection = 0
		self.typechoice.SetSelection(selection)
		self.dialogsizer.Layout()
		self.Thaw()

	def getValues(self):
		return (self.launcherchoice.GetStringSelection(),
						self.typechoice.GetStringSelection(),
						self.nametextctrl.GetValue())

	def onCreate(self, evt):
		name = self.nametextctrl.GetValue()
		e = None

		if not name:
			e = 'Invalid node name.'
		elif name in self.nodenames:
			e = 'Node name in use.'

		if e is None:
			evt.Skip()
		else:
			dlg = wx.MessageDialog(self, e, 'Node Create Error', wx.OK|wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()

class BindEventDialog(wx.Dialog):
	def __init__(self, parent, nodenames, eventio, eventclasses, distmap):
		self.nodenames = nodenames
		self.eventio = eventio
		self.eventclasses = eventclasses
		self.distmap = distmap
		wx.Dialog.__init__(self, parent, -1, 'Bind Events')

		self.dialogsizer = wx.GridBagSizer()

		sizer = wx.GridBagSizer(3, 3)

		sizer.Add(
				wx.StaticText(self, -1, 'Double click on an event to bind or unbind.'),
							(0, 0), (1, 3), wx.ALIGN_CENTER)

		sizer.Add(wx.StaticText(self, -1, 'From:'), (1, 0), (1, 1),
																									wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(wx.StaticText(self, -1, 'Events:'), (1, 1), (1, 1),
																									wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(wx.StaticText(self, -1, 'To:'), (1, 2), (1, 1),
																									wx.ALIGN_CENTER_VERTICAL)

		self.fromlistbox = wx.ListBox(self, -1, choices=nodenames)
		self.unboundeventlistbox = wx.ListBox(self, -1, choices=eventclasses.keys(),
																					style=wx.LB_SORT)
		self.boundeventlistbox = wx.ListBox(self, -1, choices=eventclasses.keys(),
																				style=wx.LB_SORT)
		self.tolistbox = wx.ListBox(self, -1, choices=nodenames)
		sizer.Add(self.fromlistbox, (2, 0), (4, 1), wx.EXPAND)
		sizer.Add(wx.StaticText(self, -1, 'Unbound:'), (2, 1), (1, 1),
																										wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.unboundeventlistbox, (3, 1), (1, 1), wx.EXPAND)
		sizer.Add(wx.StaticText(self, -1, 'Bound:'), (4, 1), (1, 1),
																										wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.boundeventlistbox, (5, 1), (1, 1), wx.EXPAND)
		sizer.Add(self.tolistbox, (2, 2), (4, 1), wx.EXPAND)
		self.Bind(wx.EVT_LISTBOX, self.onFromSelect, self.fromlistbox)
		self.Bind(wx.EVT_LISTBOX, self.onToSelect, self.tolistbox)

		self.Bind(wx.EVT_LISTBOX_DCLICK, self.onUnboundDoubleClicked,
							self.unboundeventlistbox)
		self.Bind(wx.EVT_LISTBOX_DCLICK, self.onBoundDoubleClicked,
							self.boundeventlistbox)

		buttonsizer = wx.GridBagSizer(0, 3)
		donebutton = wx.Button(self, wx.ID_OK, 'Done')
		donebutton.SetDefault()
		buttonsizer.Add(donebutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
		buttonsizer.AddGrowableCol(0)
		sizer.Add(buttonsizer, (6, 0), (1, 3), wx.EXPAND)

		for lb in [self.boundeventlistbox, self.unboundeventlistbox]:
			sizer.SetItemMinSize(lb, (-1, lb.GetSize()[1]/2))

		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def onUnboundDoubleClicked(self, evt):
		fromname = self.fromlistbox.GetStringSelection()
		toname = self.tolistbox.GetStringSelection()
		if fromname and toname:
			eventclass = self.eventclasses[evt.GetString()]
			self.GetParent().manager.addEventDistmap(eventclass, fromname, toname)
			self.unboundeventlistbox.Delete(evt.GetSelection())
			self.boundeventlistbox.Append(evt.GetString())

	def onBoundDoubleClicked(self, evt):
		fromname = self.fromlistbox.GetStringSelection()
		toname = self.tolistbox.GetStringSelection()
		if fromname and toname:
			eventclass = self.eventclasses[evt.GetString()]
			self.GetParent().manager.delEventDistmap(eventclass, fromname, toname)
			self.boundeventlistbox.Delete(evt.GetSelection())
			self.unboundeventlistbox.Append(evt.GetString())

	def isBound(self, eventclass, fromname, toname):
		try:
			if toname in self.distmap[eventclass][fromname]:
				return True
			else:
				return False
		except KeyError:
			return False

	def getCommonEvents(self, fromname, toname):
		outputs = self.eventio[fromname]['outputs']
		inputs = self.eventio[toname]['inputs']
		boundevents = []
		unboundevents = []
		for output in outputs:
			if output in inputs:
				if self.isBound(output, fromname, toname):
					boundevents.append(output.__name__)
				else:
					unboundevents.append(output.__name__)
		return boundevents, unboundevents

	def onFromSelect(self, evt):
		name = evt.GetString()

		toname = self.tolistbox.GetStringSelection()
		if not toname or name == toname:
			bound, unbound = [], []
		else:
			bound, unbound = self.getCommonEvents(name, toname)

		self.boundeventlistbox.Clear()
		self.boundeventlistbox.AppendItems(bound)
		self.unboundeventlistbox.Clear()
		self.unboundeventlistbox.AppendItems(unbound)

	def onToSelect(self, evt):
		name = evt.GetString()

		fromname = self.fromlistbox.GetStringSelection()
		if not fromname or name == fromname:
			bound, unbound = [], []
		else:
			bound, unbound = self.getCommonEvents(fromname, name)

		self.boundeventlistbox.Clear()
		self.boundeventlistbox.AppendItems(bound)
		self.unboundeventlistbox.Clear()
		self.unboundeventlistbox.AppendItems(unbound)

class RunApplicationDialog(wx.Dialog):
	def __init__(self, parent, apps, launchernames, history):
		self.apps = apps
		self.launchernames = launchernames

		history.reverse()
		names = apps.keys()
		for n in history:
			if n in names:
				names.remove(n)
				names.insert(0, n)
		self.history = names

		wx.Dialog.__init__(self, parent, -1, 'Run Application')

		self.dialogsizer = wx.GridBagSizer()
		self.sizer = wx.GridBagSizer(5, 5)

		self.sizer.Add(wx.StaticText(self, -1, 'Application:'), (0, 0), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)

		self.sortbycheckbox = wx.CheckBox(self, -1, 'Sort by last used')
		if self.sortbycheckbox.GetValue():
			names = self.history
		else:
			names = apps.keys()
			names.sort()
		self.appchoice = wx.Choice(self, -1, choices=names)
		self.sizer.Add(self.appchoice, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.sizer.Add(self.sortbycheckbox, (1, 0), (1, 2), wx.ALIGN_CENTER)
		self.launchersizer = None
		self.launcherlabels = []
		self.launcherchoices = {}
		self.appchoice.SetSelection(0)
		self.onChoice()
		self.Bind(wx.EVT_CHOICE, self.onChoice, self.appchoice)
		self.Bind(wx.EVT_CHECKBOX, self.onCheckBox, self.sortbycheckbox)

		buttonsizer = wx.GridBagSizer(0, 3)
		runbutton = wx.Button(self, wx.ID_OK, 'Run')
		runbutton.SetDefault()
		buttonsizer.Add(runbutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

		cancelbutton = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		buttonsizer.Add(cancelbutton, (0, 1), (1, 1), wx.ALIGN_CENTER)

		buttonsizer.AddGrowableCol(0)

		self.sizer.Add(buttonsizer, (3, 0), (1, 2), wx.EXPAND)

		self.dialogsizer.Add(self.sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def onChoice(self, evt=None):
		if evt is None:
			name = self.appchoice.GetStringSelection()
		else:
			name = evt.GetString()
		self.app = self.apps[name]
		launcheraliases = self.app.getLauncherAliases()
		if self.launchersizer is not None:
			self.sizer.Remove(self.launchersizer)
			for label in self.launcherlabels:
				label.Destroy()
			for choice in self.launcherchoices.values():
				choice.Destroy()
			self.launchersizer = None
			self.launcherlabels = []
			self.launcherchoices = {}
		if launcheraliases:
			self.launchersizer = wx.GridBagSizer(5, 5)
			for i, launcheralias in enumerate(launcheraliases):
				label = wx.StaticText(self, -1, launcheralias + ':')
				self.launcherlabels.append(label)
				self.launchersizer.Add(label, (i, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
				choice = wx.Choice(self, -1, choices=self.launchernames)
				choice.SetSelection(0)
				self.launchersizer.Add(choice, (i, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
				self.launcherchoices[launcheralias] = choice
		self.sizer.Add(self.launchersizer, (2, 0), (1, 2), wx.ALIGN_CENTER)
		self.dialogsizer.Layout()
		self.Fit()

	def onCheckBox(self, evt):
		selection = self.appchoice.GetStringSelection()
		self.appchoice.Clear()
		if evt.IsChecked():
			names = self.history
		else:
			names = self.apps.keys()
			names.sort()
		self.appchoice.AppendItems(names)
		self.appchoice.SetStringSelection(selection)

	def getValues(self):
		for alias, choice in self.launcherchoices.items():
			self.app.setLauncherAlias(alias, choice.GetStringSelection())
		return self.app

class ExportApplicationDialog(wx.Dialog):
	def __init__(self, parent, names):
		self.names = names
		wx.Dialog.__init__(self, parent, -1, 'Export Application')

		self.dialogsizer = wx.GridBagSizer()
		sizer = wx.GridBagSizer(5, 5)

		sizer.Add(wx.StaticText(self, -1, 'Application:'), (0, 0), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)
		self.appchoice = wx.Choice(self, -1, choices=names)
		self.appchoice.SetSelection(0)
		sizer.Add(self.appchoice, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		sizer.Add(wx.StaticText(self, -1, 'File name:'), (1, 0), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)
		self.filenametextctrl = wx.TextCtrl(self, -1, '')
		sizer.Add(self.filenametextctrl, (1, 1), (1, 1),
							wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
		browsebutton = wx.Button(self, -1, 'Browse...')
		sizer.Add(browsebutton, (1, 2), (1, 1), wx.ALIGN_CENTER)
		self.Bind(wx.EVT_BUTTON, self.onBrowse, browsebutton)

		buttonsizer = wx.GridBagSizer(0, 3)
		exportbutton = wx.Button(self, wx.ID_OK, 'Export')
		exportbutton.SetDefault()
		buttonsizer.Add(exportbutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

		cancelbutton = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		buttonsizer.Add(cancelbutton, (0, 1), (1, 1), wx.ALIGN_CENTER)

		buttonsizer.AddGrowableCol(0)

		sizer.Add(buttonsizer, (2, 0), (1, 3), wx.EXPAND)

		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def onBrowse(self, evt):
		dlg = wx.FileDialog(self, 'Export Application',
												defaultFile=self.filenametextctrl.GetValue(),
												wildcard='XML file (*.xml)|*.xml|'\
																	'All files (*.*)|*.*',
												style=wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			self.filenametextctrl.SetValue(dlg.GetPath())
		dlg.Destroy()

	def getValues(self):
		return self.filenametextctrl.GetValue(), self.appchoice.GetStringSelection()

