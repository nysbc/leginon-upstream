import event
import logging
import manager
import os
import threading
import uiclient
import wx
import wx.lib.intctrl

AddNodeEventType = wx.NewEventType()
RemoveNodeEventType = wx.NewEventType()
AddLauncherEventType = wx.NewEventType()
RemoveLauncherEventType = wx.NewEventType()
ApplicationStartingEventType = wx.NewEventType()
ApplicationNodeStartedEventType = wx.NewEventType()
ApplicationStartedEventType = wx.NewEventType()
ApplicationKilledEventType = wx.NewEventType()
EVT_ADD_NODE = wx.PyEventBinder(AddNodeEventType)
EVT_REMOVE_NODE = wx.PyEventBinder(RemoveNodeEventType)
EVT_ADD_LAUNCHER = wx.PyEventBinder(AddLauncherEventType)
EVT_REMOVE_LAUNCHER = wx.PyEventBinder(RemoveLauncherEventType)
EVT_APPLICATION_STARTING = wx.PyEventBinder(ApplicationStartingEventType)
EVT_APPLICATION_NODE_STARTED = wx.PyEventBinder(ApplicationNodeStartedEventType)
EVT_APPLICATION_STARTED = wx.PyEventBinder(ApplicationStartedEventType)
EVT_APPLICATION_KILLED = wx.PyEventBinder(ApplicationKilledEventType)

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

class ManagerApp(wx.App):
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

class ManagerStatusBar(wx.StatusBar):
	def __init__(self, parent):
		wx.StatusBar.__init__(self, parent, -1)

class ManagerFrame(wx.Frame):
	def __init__(self, manager):
		self.manager = manager

		wx.Frame.__init__(self, None, -1, 'Manager', size=(750, 750))

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
		self.statusbar = ManagerStatusBar(self)
		self.SetStatusBar(self.statusbar)

		self.applicationprogressdialog = None

		self.Bind(EVT_ADD_NODE, self.onAddNode)
		self.Bind(EVT_REMOVE_NODE, self.onRemoveNode)
		self.Bind(EVT_ADD_LAUNCHER, self.onAddLauncher)
		self.Bind(EVT_REMOVE_LAUNCHER, self.onRemoveLauncher)
		self.Bind(EVT_APPLICATION_STARTING, self.onApplicationStarting)
		self.Bind(EVT_APPLICATION_NODE_STARTED, self.onApplicationNodeStarted)
		self.Bind(EVT_APPLICATION_STARTED, self.onApplicationStarted)
		self.Bind(EVT_APPLICATION_KILLED, self.onApplicationKilled)

		self.panel = ManagerPanel(self, self.manager.uicontainer.location())

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
			threading.Thread(name='wxManager runApplication',
												target=self.manager.runApplication,
												args=(app,)).start()
		dialog.Destroy()

	def onMenuKillApplication(self, evt):
		threading.Thread(name='wxManager killApplication',
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
		dialog = LoggingConfigurationDialog(self)
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
		dlg = wx.ProgressDialog('Starting %s...' % evt.name,
														'Starting application %s' % evt.name,
														maximum=evt.nnodes, parent=self,
														style=wx.PD_APP_MODAL)
		dlg.count = 0
		self.applicationprogressdialog = dlg

	def onApplicationNodeStarted(self, evt):
		dlg = self.applicationprogressdialog
		if dlg is not None:
			dlg.count += 1
			dlg.Update(dlg.count, 'Started %s node' % evt.name)

	def onApplicationStarted(self, evt):
		self.killappmenuitem.Enable(True)
		if self.applicationprogressdialog is not None:
			self.applicationprogressdialog.Destroy()

	def onApplicationKilled(self, evt):
		self.killappmenuitem.Enable(False)
		if self.manager.getLauncherCount() > 0:
			self.runappmenuitem.Enable(True)

class ManagerPanel(wx.ScrolledWindow):
	def __init__(self, parent, location):
		self._enabled = True
		self._shown = True
		wx.ScrolledWindow.__init__(self, parent, -1)
		self.SetScrollRate(5, 5)
		containerclass = uiclient.SimpleContainerWidget
		containerclass = uiclient.ClientContainerFactory(containerclass)
		self.container = containerclass('UI Client', self, self, location, {})
		self.SetSizer(self.container)
		self.Fit()

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

		sizer = wx.GridBagSizer(5, 5)

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

class LoggingConfigurationDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, -1, 'Logging Configuration')

		self.dialogsizer = wx.GridBagSizer()
		sizer = wx.GridBagSizer(5, 5)

		self.tree = wx.TreeCtrl(self, -1)#, style=wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS)
		sizer.Add(self.tree, (0, 0), (5, 1), wx.EXPAND)

		self.cbpropagate = wx.CheckBox(self, -1, 'Propagate')
		self.Bind(wx.EVT_CHECKBOX, self.onPropagateCheckbox, self.cbpropagate)
		sizer.Add(self.cbpropagate, (0, 1), (1, 2), wx.ALIGN_CENTER_VERTICAL)

		sizer.Add(wx.StaticText(self, -1, 'Level:'), (1, 1), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)
		self.clevel = wx.Choice(self, -1, choices=self._getLevelNames())
		self.clevel.SetSelection(0)
		self.Bind(wx.EVT_CHOICE, self.onLevelChoice, self.clevel)
		sizer.Add(self.clevel, (1, 2), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		self.cbprint = wx.CheckBox(self, -1, 'Print')
		self.Bind(wx.EVT_CHECKBOX, self.onPrintCheckbox, self.cbprint)
		sizer.Add(self.cbprint, (2, 1), (1, 2), wx.ALIGN_CENTER_VERTICAL)

		sizer.Add(wx.StaticText(self, -1, 'Format:'), (3, 1), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)
		self.tcformat = wx.TextCtrl(self, -1, '')
		sizer.Add(self.tcformat, (3, 2), (1, 1),
							wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
		self.Bind(wx.EVT_TEXT, self.onFormat, self.tcformat)

		sizer.Add(wx.StaticText(self, -1, 'Date Format:'), (4, 1), (1, 1),
							wx.ALIGN_CENTER_VERTICAL)
		self.tcdateformat = wx.TextCtrl(self, -1, '')
		sizer.Add(self.tcdateformat, (4, 2), (1, 1),
							wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
		self.Bind(wx.EVT_TEXT, self.onDateFormat, self.tcdateformat)

		sizer.AddGrowableCol(2)

		buttonsizer = wx.GridBagSizer(0, 0)
		donebutton = wx.Button(self, wx.ID_OK, 'Done')
		donebutton.SetDefault()
		buttonsizer.Add(donebutton, (0, 0), (1, 1),
										wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
		buttonsizer.AddGrowableCol(0)
		sizer.Add(buttonsizer, (5, 1), (1, 3), wx.EXPAND)

		self.setTree()
		self.onTreeSelectionChanged()
		sizer.SetItemMinSize(self.tree, (self.tree.GetSize()[0]*2, -1))

		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSelectionChanged, self.tree)
		self.dialogsizer.Add(sizer, (0, 0), (1, 1), wx.ALIGN_CENTER|wx.ALL, 10)
		self.SetSizerAndFit(self.dialogsizer)

	def onPropagateCheckbox(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		logger.propagate = evt.IsChecked()

	def onLevelChoice(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		logger.setLevel(evt.GetString())

	def onPrintCheckbox(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		if evt.IsChecked():
			logger.addPrintHandler()
		else:
			logger.removePrintHandler()

	def onFormat(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		if logger is logging.root:
			return
		logger.format = evt.GetString() 
		logger.setPrintFormatter()

	def onDateFormat(self, evt):
		logger = self.tree.GetPyData(self.tree.GetSelection())
		if logger is logging.root:
			return
		logger.dateformat = evt.GetString() 
		logger.setPrintFormatter()

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

	def onTreeSelectionChanged(self, evt=None):
		if evt is None:
			logger = self.tree.GetPyData(self.tree.GetSelection())
		else:
			logger = self.tree.GetPyData(evt.GetItem())

		enable = not logger is logging.root
		self.cbpropagate.Enable(enable)
		self.clevel.Enable(enable)
		self.cbprint.Enable(enable)
		self.tcformat.Enable(enable)
		self.tcdateformat.Enable(enable)

		self.cbpropagate.SetValue(logger.propagate)
		level = self._getLevel(logger)
		if type(level) is not str:
			level = logging.getLevelName(level)
		self.clevel.SetStringSelection(level)
		if enable:
			self.cbprint.SetValue(logger.hasPrintHandler())
			self.tcformat.SetValue(logger.format)
			self.tcdateformat.SetValue(logger.dateformat)
		else:
			self.cbprint.SetValue(False)
			self.tcformat.SetValue('')
			self.tcdateformat.SetValue('')

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

