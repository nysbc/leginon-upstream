# The Leginon software is Copyright 2004
# The Scripps Research Institute, La Jolla, CA
# For terms of the license agreement
# see http://ami.scripps.edu/software/leginon-license
#
# $Source: /ami/sw/cvsroot/pyleginon/gui/wx/BeamTiltCalibrator.py,v $
# $Revision: 1.16 $
# $Name: not supported by cvs2svn $
# $Date: 2006-03-10 19:12:57 $
# $Author: suloway $
# $State: Exp $
# $Locker:  $

import threading
import wx
import gui.wx.Calibrator
from gui.wx.Entry import FloatEntry
import gui.wx.Settings
import gui.wx.ToolBar

class SettingsDialog(gui.wx.Calibrator.SettingsDialog):
	def initialize(self):
		sizers = gui.wx.Calibrator.SettingsDialog.initialize(self)

		self.widgets['measure beam tilt'] = FloatEntry(self, -1, chars=7)
		self.widgets['stig lens'] = wx.Choice(self, -1, choices=['objective', 'diffraction'])
		self.widgets['correct tilt'] = wx.CheckBox(self, -1, 'Correct image for tilt')
		sizer = wx.GridBagSizer(5, 5)
		label = wx.StaticText(self, -1, 'Measure beam tilt (+/-)')
		sizer.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.widgets['measure beam tilt'], (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE)
		label = wx.StaticText(self, -1, 'Measure stig. lens')
		sizer.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.widgets['stig lens'], (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sizer.Add(self.widgets['correct tilt'], (0, 2), (2, 1), wx.ALIGN_CENTER)

		sizer.AddGrowableRow(0)
		sizer.AddGrowableCol(2)

		sb = wx.StaticBox(self, -1, 'Beam Tilt')
		sbsz = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbsz.Add(sizer, 0, wx.EXPAND|wx.ALL, 5)

		return sizers + [sbsz]

class Panel(gui.wx.Calibrator.Panel):
	icon = 'beamtilt'
	settingsclass = SettingsDialog
	def initialize(self):
		gui.wx.Calibrator.Panel.initialize(self)

		choices = ['Defocus', 'Stigmator']
		self.parameter = wx.Choice(self.toolbar, -1, choices=choices)
		self.parameter.SetSelection(0)

		self.toolbar.InsertControl(5, self.parameter)
		self.toolbar.InsertTool(6, gui.wx.ToolBar.ID_PARAMETER_SETTINGS, 'settings', shortHelpString='Parameter Settings')
		self.toolbar.AddSeparator()
		self.toolbar.AddTool(gui.wx.ToolBar.ID_MEASURE, 'ruler', shortHelpString='Measure')
		self.toolbar.AddSeparator()
		self.toolbar.AddTool(gui.wx.ToolBar.ID_GET_INSTRUMENT, 'focusget', shortHelpString='Eucentric Focus From Scope')
		self.toolbar.AddTool(gui.wx.ToolBar.ID_SET_INSTRUMENT, 'focusset', shortHelpString='Eucentric Focus To Scope')
		self.toolbar.AddTool(gui.wx.ToolBar.ID_GET_BEAMTILT, 'beamtiltget', shortHelpString='Rotation Center From Scope')
		self.toolbar.AddTool(gui.wx.ToolBar.ID_SET_BEAMTILT, 'beamtiltset', shortHelpString='Rotation Center To Scope')

		self.toolbar.EnableTool(gui.wx.ToolBar.ID_ABORT, False)

		self.Bind(gui.wx.Events.EVT_GET_INSTRUMENT_DONE, self.onGetInstrumentDone)
		self.Bind(gui.wx.Events.EVT_SET_INSTRUMENT_DONE, self.onSetInstrumentDone)
		self.Bind(gui.wx.Events.EVT_MEASUREMENT_DONE, self.onMeasurementDone)

	def onNodeInitialized(self):
		gui.wx.Calibrator.Panel.onNodeInitialized(self)

		self.measure_dialog = MeasureDialog(self)

		self.toolbar.Bind(wx.EVT_TOOL, self.onParameterSettingsTool, id=gui.wx.ToolBar.ID_PARAMETER_SETTINGS)
		self.toolbar.Bind(wx.EVT_TOOL, self.onMeasureTool, id=gui.wx.ToolBar.ID_MEASURE)
		self.toolbar.Bind(wx.EVT_TOOL, self.onEucentricFocusFromScope, id=gui.wx.ToolBar.ID_GET_INSTRUMENT)
		self.toolbar.Bind(wx.EVT_TOOL, self.onEucentricFocusToScope, id=gui.wx.ToolBar.ID_SET_INSTRUMENT)
		self.toolbar.Bind(wx.EVT_TOOL, self.onRotationCenterFromScope, id=gui.wx.ToolBar.ID_GET_BEAMTILT)
		self.toolbar.Bind(wx.EVT_TOOL, self.onRotationCenterToScope, id=gui.wx.ToolBar.ID_SET_BEAMTILT)

	def instrumentEnable(self, enable):
		tools = [
			gui.wx.ToolBar.ID_ACQUIRE,
			gui.wx.ToolBar.ID_CALIBRATE,
			#gui.wx.ToolBar.ID_MEASURE,
			gui.wx.ToolBar.ID_GET_INSTRUMENT,
			gui.wx.ToolBar.ID_SET_INSTRUMENT,
			gui.wx.ToolBar.ID_GET_BEAMTILT,
			gui.wx.ToolBar.ID_SET_BEAMTILT,
		]
		for tool in tools:
			self.toolbar.EnableTool(tool, enable)

		self.measure_dialog.measure.Enable(enable)
		if self.node.measurement:
			self.measure_dialog.correctdefocus.Enable(enable)
			self.measure_dialog.correctstig.Enable(enable)
		self.measure_dialog.resetdefocus.Enable(enable)

	def _acquisitionEnable(self, enable):
		self.instrumentEnable(enable)
		self.toolbar.EnableTool(gui.wx.ToolBar.ID_SETTINGS, enable)

	def _calibrationEnable(self, enable):
		self._acquisitionEnable(enable)
		self.parameter.Enable(enable)
		self.toolbar.EnableTool(gui.wx.ToolBar.ID_PARAMETER_SETTINGS, enable)
		self.toolbar.EnableTool(gui.wx.ToolBar.ID_ABORT, not enable)

	def onGetInstrumentDone(self, evt):
		self.instrumentEnable(True)

	def onSetInstrumentDone(self, evt):
		self.instrumentEnable(True)

	def onMeasurementDone(self, evt):
		self._calibrationEnable(True)

		if evt.defocus is None:
			label = '(Not measured)'
		else:
			label = '%g' % evt.defocus
		self.measure_dialog.labels['defocus'].SetLabel(label)

		for axis, value in evt.stig.items():
			if value is None:
				label = '(Not measured)'
			else:
				label = '%g' % value
			self.measure_dialog.labels['stigmator'][axis].SetLabel(label)

		self.measure_dialog.sizer.Layout()
		self.measure_dialog.Fit()

	def measurementDone(self, defocus, stig):
		evt = gui.wx.Events.MeasurementDoneEvent()
		evt.defocus = defocus
		evt.stig = stig
		self.GetEventHandler().AddPendingEvent(evt)

	def onEucentricFocusToScope(self, evt):
		self.instrumentEnable(False)
		threading.Thread(target=self.node.eucentricFocusToScope).start()

	def onEucentricFocusFromScope(self, evt):
		self.instrumentEnable(False)
		threading.Thread(target=self.node.eucentricFocusFromScope).start()

	def onRotationCenterToScope(self, evt):
		self.instrumentEnable(False)
		threading.Thread(target=self.node.rotationCenterToScope).start()

	def onRotationCenterFromScope(self, evt):
		self.instrumentEnable(False)
		threading.Thread(target=self.node.rotationCenterFromScope).start()

	def onMeasureTool(self, evt):
		self.measure_dialog.Show()

	def onParameterSettingsTool(self, evt):
		parameter = self.parameter.GetStringSelection()
		if parameter == 'Defocus':
			dialog = DefocusSettingsDialog(self)
		elif parameter == 'Stigmator':
			dialog = StigmatorSettingsDialog(self)
		else:
			raise RuntimeError
		dialog.ShowModal()
		dialog.Destroy()

	def onCalibrateTool(self, evt):
		self._calibrationEnable(False)
		parameter = self.parameter.GetStringSelection()
		if parameter == 'Defocus':
			threading.Thread(target=self.node.calibrateDefocus).start()
		elif parameter == 'Stigmator':
			threading.Thread(target=self.node.calibrateStigmator).start()
		else:
			raise RuntimeError

	def onAbortTool(self, evt):
		self.node.abortCalibration()

class DefocusSettingsDialog(gui.wx.Settings.Dialog):
	def initialize(self):
		gui.wx.Settings.Dialog.initialize(self)

		self.widgets['defocus beam tilt'] = FloatEntry(self, -1, chars=9)
		self.widgets['first defocus'] = FloatEntry(self, -1, chars=9)
		self.widgets['second defocus'] = FloatEntry(self, -1, chars=9)

		sz = wx.GridBagSizer(5, 5)
		label = wx.StaticText(self, -1, 'Beam tilt (+/-)')
		sz.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['defocus beam tilt'], (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)
		label = wx.StaticText(self, -1, 'First defocus')
		sz.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['first defocus'], (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)
		label = wx.StaticText(self, -1, 'Second defocus')
		sz.Add(label, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['second defocus'], (2, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)

		sb = wx.StaticBox(self, -1, 'Defocus Calibration')
		sbsz = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbsz.Add(sz, 0, wx.ALIGN_CENTER|wx.ALL, 5)

		return [sbsz]

class StigmatorSettingsDialog(gui.wx.Settings.Dialog):
	def initialize(self):
		gui.wx.Settings.Dialog.initialize(self)

		self.widgets['stig lens'] = wx.Choice(self, -1, choices=['objective', 'diffraction'])
		self.widgets['stig lens'].SetSelection(0)
		self.widgets['stig beam tilt'] = FloatEntry(self, -1, chars=9)
		self.widgets['stig delta'] = FloatEntry(self, -1, chars=9)

		sz = wx.GridBagSizer(5, 5)

		label = wx.StaticText(self, -1, 'Lens')
		sz.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['stig lens'], (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)

		label = wx.StaticText(self, -1, 'Beam tilt (+/-)')
		sz.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['stig beam tilt'], (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)

		label = wx.StaticText(self, -1, 'Delta stig')
		sz.Add(label, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		sz.Add(self.widgets['stig delta'], (2, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.FIXED_MINSIZE|wx.ALIGN_RIGHT)

		sb = wx.StaticBox(self, -1, 'Stigmator Calibration')
		sbsz = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbsz.Add(sz, 0, wx.ALIGN_CENTER|wx.ALL, 5)

		return [sbsz]

class MeasureDialog(wx.Dialog):
	def __init__(self, parent):
		self.node = parent.node

		wx.Dialog.__init__(self, parent, -1, 'Measure Defocus/Stig.')

		self.labels = {}
		self.labels['defocus'] = wx.StaticText(self, -1, '(Not measured)')
		self.labels['stigmator'] = {}
		for axis in ('x', 'y'):
			self.labels['stigmator'][axis] = wx.StaticText(self, -1, '(Not measured)')

		szresult = wx.GridBagSizer(5, 5)
		label = wx.StaticText(self, -1, 'Defocus')
		szresult.Add(label, (0, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szresult.Add(self.labels['defocus'], (0, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		label = wx.StaticText(self, -1, 'Stig. x')
		szresult.Add(label, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szresult.Add(self.labels['stigmator']['x'], (1, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		label = wx.StaticText(self, -1, 'Stig. y')
		szresult.Add(label, (2, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szresult.Add(self.labels['stigmator']['y'], (2, 1), (1, 1), wx.ALIGN_CENTER_VERTICAL)
		szresult.AddGrowableRow(0)
		szresult.AddGrowableRow(1)
		szresult.AddGrowableRow(2)
		szresult.AddGrowableCol(0)

		self.measure = wx.Button(self, -1, 'Measure')
		self.correctdefocus = wx.Button(self, -1, 'Correct Defocus')
		self.correctstig = wx.Button(self, -1, 'Correct Stig.')
		self.resetdefocus = wx.Button(self, -1, 'Reset Defocus')
		self.correctdefocus.Enable(False)
		self.correctstig.Enable(False)

		szbutton = wx.GridBagSizer(5, 5)
		szbutton.Add(self.measure, (0, 0), (1, 1), wx.EXPAND)
		szbutton.Add(self.correctdefocus, (1, 0), (1, 1), wx.EXPAND)
		szbutton.Add(self.correctstig, (2, 0), (1, 1), wx.EXPAND)
		szbutton.Add(self.resetdefocus, (3, 0), (1, 1), wx.EXPAND)

		sz = wx.GridBagSizer(5, 20)
		sz.Add(szresult, (0, 0), (1, 1), wx.ALIGN_CENTER)
		sz.Add(szbutton, (0, 1), (1, 1), wx.ALIGN_CENTER)

		sb = wx.StaticBox(self, -1, 'Parameters')
		sbsz = wx.StaticBoxSizer(sb, wx.VERTICAL)
		sbsz.Add(sz, 0, wx.ALIGN_CENTER|wx.ALL, 5)

		self.done = wx.Button(self, wx.ID_OK, 'Close')

		self.sizer = wx.GridBagSizer(5, 5)
		self.sizer.Add(sbsz, (0, 0), (1, 1), wx.EXPAND|wx.ALL, 10)
		self.sizer.Add(self.done, (1, 0), (1, 1), wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 10)

		self.SetSizerAndFit(self.sizer)

		self.Bind(wx.EVT_BUTTON, self.onMeasureButton, self.measure)
		self.Bind(wx.EVT_BUTTON, self.onCorrectDefocusButton, self.correctdefocus)
		self.Bind(wx.EVT_BUTTON, self.onCorrectStigButton, self.correctstig)
		self.Bind(wx.EVT_BUTTON, self.onResetDefocusButton, self.resetdefocus)

	def onMeasureButton(self, evt):
		self.GetParent()._calibrationEnable(False)
		threading.Thread(target=self.node.measure).start()

	def onCorrectDefocusButton(self, evt):
		self.GetParent().instrumentEnable(False)
		threading.Thread(target=self.node.correctDefocus).start()

	def onCorrectStigButton(self, evt):
		self.GetParent().instrumentEnable(False)
		threading.Thread(target=self.node.correctStigmator).start()

	def onResetDefocusButton(self, evt):
		self.GetParent().instrumentEnable(False)
		threading.Thread(target=self.node.resetDefocus).start()

