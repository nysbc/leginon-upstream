import wx
import wx.lib.masked
from wx.lib.intctrl import IntCtrl, EVT_INT
import gui.wx.Data
import gui.wx.Node
import wxImageViewer

class Panel(gui.wx.Node.Panel):
	icon = 'acquisition'
	def __init__(self, parent, name):
		gui.wx.Node.Panel.__init__(self, parent, -1, name='%s.pAcquisition' % name)

		self.szmain = wx.GridBagSizer(5, 5)

		# status
		self.szstatus = self._getStaticBoxSizer('Status', (0, 0), (1, 2),
																						wx.EXPAND|wx.ALL)
		self.ststatus = wx.StaticText(self, -1, '')
		self.szstatus.Add(self.ststatus, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		# settings
		self.szsettings = self._getStaticBoxSizer('Settings', (1, 0), (1, 1),
																							wx.EXPAND|wx.ALL)

		label = wx.StaticText(self, -1, 'Frames to average:')
		self.szsettings.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.icnaverage = IntCtrl(self, -1, 3, min=1, max=99, limited=True,
															style=wx.TE_RIGHT, name='icNAverage')
		self.szsettings.Add(self.icnaverage, (0, 1), (1, 1),
												wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		# camera size
		self.cpcamconfig = gui.wx.Camera.CameraPanel(self)
		self.szsettings.Add(self.cpcamconfig, (1, 0), (1, 2), wx.EXPAND|wx.ALL)

		szplan = wx.GridBagSizer(5, 5)
		label = wx.StaticText(self, -1, 'Bad rows:')
		szplan.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.stbadrows = wx.StaticText(self, -1)
		szplan.Add(self.stbadrows, (0, 1), (1, 1),
								wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		label = wx.StaticText(self, -1, 'Bad columns:')
		szplan.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.stbadcolumns = wx.StaticText(self, -1)
		szplan.Add(self.stbadcolumns, (1, 1), (1, 1),
								wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)

		szplan.AddGrowableCol(1)

		beditplan = wx.Button(self, -1, 'Edit...')
		szplan.Add(beditplan, (2, 1), (1, 2),
												wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)

		sb = wx.StaticBox(self, -1, 'Plan')
		sbszplan = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbszplan.Add(szplan, 1, wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 3)
		self.szsettings.Add(sbszplan, (2, 0), (1, 2),
												wx.ALIGN_CENTER|wx.EXPAND|wx.ALL)
		
		szdespike = wx.GridBagSizer(5, 5)
		self.cbdespike = wx.CheckBox(self, -1, 'Despike images')
		szdespike.Add(self.cbdespike, (0, 0), (1, 2), wx.ALIGN_CENTER_VERTICAL)

		label = wx.StaticText(self, -1, 'Neighborhood size:')
		szdespike.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.ncnsize = wx.lib.masked.NumCtrl(self, -1, 11, integerWidth=8,
																												fractionWidth=0,
																												allowNone=False,
																												allowNegative=False,
																												name='ncNSize')
		szdespike.Add(self.ncnsize, (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		label = wx.StaticText(self, -1, 'Threshold:')
		szdespike.Add(label, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.ncthreshold = wx.lib.masked.NumCtrl(self, -1, 3.5, integerWidth=6,
																														fractionWidth=2,
																														allowNone=False,
																														allowNegative=False,
																														name='ncNSize')
		szdespike.Add(self.ncthreshold, (2, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)

		sb = wx.StaticBox(self, -1, 'Despike')
		sbszdespike = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbszdespike.Add(szdespike, 1, wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 3)
		self.szsettings.Add(sbszdespike, (3, 0), (1, 2),
												wx.ALIGN_CENTER|wx.EXPAND|wx.ALL)
		
		# controls
		self.szcontrols = self._getStaticBoxSizer('Controls', (2, 0), (1, 1),
																wx.EXPAND|wx.ALL)
		szrb = wx.GridBagSizer(0, 0)
		self.rbdark = wx.RadioButton(self, -1, "Dark Reference", style=wx.RB_GROUP)
		self.rbbright = wx.RadioButton(self, -1, "Bright Reference")
		self.rbraw = wx.RadioButton(self, -1, "Raw Image")
		self.rbcorrected = wx.RadioButton(self, -1, "Corrected Image")
		szrb.Add(self.rbdark, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szrb.Add(self.rbbright, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szrb.Add(self.rbraw, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szrb.Add(self.rbcorrected, (3, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		self.szcontrols.Add(szrb, (0, 0), (1, 1), wx.ALIGN_CENTER)

		self.bacquire = wx.Button(self, -1, 'Acquire')
		self.szcontrols.Add(self.bacquire, (1, 0), (1, 1), wx.ALIGN_CENTER)
		self.szcontrols.AddGrowableRow(0)
		self.szcontrols.AddGrowableRow(1)
		self.szcontrols.AddGrowableCol(0)

		# image
		self.szimage = self._getStaticBoxSizer('Image', (1, 1), (3, 1),
																						wx.EXPAND|wx.ALL)
		self.imagepanel = wxImageViewer.ImagePanel(self, -1)
		self.szimage.Add(self.imagepanel, (0, 0), (1, 1), wx.EXPAND|wx.ALL)

		self.szmain.AddGrowableRow(3)
		self.szmain.AddGrowableCol(1)

		self.SetSizerAndFit(self.szmain)
		self.SetupScrolling()

		self.Bind(wx.EVT_BUTTON, self.onEditPlan, beditplan)

	def setPlan(self, plan):
		self.stbadrows.SetLabel(self.plan2str(plan['rows']))
		self.stbadcolumns.SetLabel(self.plan2str(plan['columns']))
		self.plan = plan

	def onEditPlan(self, evt):
		dialog = EditPlanDialog(self)
		if dialog.ShowModal() == wx.ID_OK:
			self.setPlan(dialog.plan)
		dialog.Destroy()

	def plan2str(self, plan):
		splan = []
		for i in plan:
			if i not in splan:
				splan.append(i)
		splan.sort()
		return str(splan)[1:-1]

	def str2plan(self, string):
		strings = string.split(',')
		plan = []
		for s in strings:
			try:
				s = s.strip()
				if not s:
					continue
				i = int(s)
				if i not in plan:
					plan.append(i)
			except ValueError:
				raise ValueError
		plan.sort()
		return plan

class EditPlanDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, -1, 'Edit Plan')

		strows = wx.StaticText(self, -1, 'Bad rows:')
		stcolumns = wx.StaticText(self, -1, 'Bad columns:')
		self.tcrows = wx.TextCtrl(self, -1, parent.stbadrows.GetLabel())
		self.tccolumns = wx.TextCtrl(self, -1, parent.stbadcolumns.GetLabel())

		bsave = wx.Button(self, wx.ID_OK, 'Save')
		bcancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')
		szbutton = wx.GridBagSizer(5, 5)
		szbutton.Add(bsave, (0, 0), (1, 1), wx.ALIGN_CENTER)
		szbutton.Add(bcancel, (0, 1), (1, 1), wx.ALIGN_CENTER)

		sz = wx.GridBagSizer(5, 5)
		sz.Add(strows, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.tcrows, (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(stcolumns, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.tccolumns, (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(szbutton, (2, 0), (1, 2), wx.ALIGN_RIGHT|wx.ALL, border=5)

		self.SetSizerAndFit(sz)

		self.Bind(wx.EVT_BUTTON, self.onSave, bsave)

	def onSave(self, evt):
		try:
			rows = self.GetParent().str2plan(self.tcrows.GetValue())
			columns = self.GetParent().str2plan(self.tccolumns.GetValue())
		except ValueError:
			dialog = wx.MessageDialog(self, 'Invalid plan', 'Error',
																wx.OK|wx.ICON_ERROR)
			dialog.ShowModal()
			dialog.Destroy()
		else:
			self.plan = {'rows': rows, 'columns': columns}
			evt.Skip()

if __name__ == '__main__':
	class App(wx.App):
		def OnInit(self):
			frame = wx.Frame(None, -1, 'Camera Test')
			panel = Panel(frame, 'Test')
			frame.Fit()
			self.SetTopWindow(frame)
			frame.Show()
			return True

	app = App(0)
	app.MainLoop()

