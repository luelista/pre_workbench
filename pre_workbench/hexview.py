#!/usr/bin/python3
# -*- coding: utf-8 -*-
# PRE Workbench
# Copyright (C) 2019 Max Weller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import traceback
from math import ceil, floor

from PyQt5 import QtCore
from PyQt5.QtCore import (Qt, QSize, pyqtSignal, QObject)
from PyQt5.QtGui import QPainter, QFont, QColor, QPixmap, QFontMetrics, QKeyEvent, QStatusTipEvent
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSizePolicy, QFileDialog, QTreeWidget, QTreeWidgetItem, \
	QTreeWidgetItemIterator, QMessageBox, QAction

from pre_workbench.textfile import showScintillaDialog
from pre_workbench import configs
from pre_workbench import structinfo
from pre_workbench.genericwidgets import showSettingsDlg
from pre_workbench.guihelper import setClipboardText, str_ellipsis
from pre_workbench.hexview_selheur import selectionHelpers
from pre_workbench.objects import ByteBuffer, Range, parseHexFromClipboard, BidiByteBuffer
from pre_workbench.typeeditor import showTypeEditorDlg, showTreeEditorDlg


class InteractiveFormatInfoContainer(structinfo.FormatInfoContainer):
	def __init__(self, parent, **kw):
		super().__init__(**kw)
		self.parent = parent

	def get_fi_by_def_name(self, def_name):
		try:
			return self.definitions[def_name]
		except KeyError:
			if QMessageBox.question(self.parent, "Format Info", "Reference to undefined formatinfo '"+def_name+"'. Create it now?") == QMessageBox.Yes:
				params = showTypeEditorDlg("format_info.tes", "AnyFI", title="Create formatinfo '"+def_name+"'")
				if params is None: raise
				self.definitions[def_name] = structinfo.deserialize_fi(params)
				return self.definitions[def_name]
			else:
				raise



class RangeTreeWidget(QTreeWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.itemActivated.connect(self.fiTreeItemActivated)
		self.setColumnCount(5)
		self.setColumnWidth(0, 400)
		self.setColumnWidth(3, 200)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		self.formatInfoContainer = None
		self.optionsConfigKey = "RangeTree"
		self.setMouseTracking(True)

	formatInfoUpdated = pyqtSignal()

	def updateTree(self, bbuf):
		self.clear()
		if bbuf.fi_tree is not None:
			root = QTreeWidgetItem(self)
			root.setExpanded(True)
			root.setText(0, self.formatInfoContainer.file_name)
			bbuf.fi_tree.addToTree(root)

	def fiTreeItemActivated(self, item, column):
		pass

	def hilightFormatInfoTree(self, range):
		iterator = QTreeWidgetItemIterator(self)
		while iterator.value():
			item = iterator.value()
			itemRange = item.data(0, Range.RangeRole)
			#item.setBackground(0, QColor("#dddddd") if itemRange is not None and itemRange.overlaps(range) else QColor("#ffffff"))
			#item.setProperty("class", "highlighted" if itemRange is not None and itemRange.overlaps(range) else "")
			iterator += 1

	def onCustomContextMenuRequested(self, point):
		ctx = QMenu("Context menu", self)
		item = self.itemAt(point)
		if item != None:
			range = item.data(0, Range.RangeRole)
			source = item.data(0, Range.SourceDescRole)

			if item.parent() != None:
				parentSource = item.parent().data(0, Range.SourceDescRole)
			if isinstance(source, structinfo.FormatInfo):
				if isinstance(source.fi, structinfo.StructFI):
					ctx.addAction("Add field ...", lambda: self.addField(source, "StructField"))
					ctx.addSeparator()
				if isinstance(source.fi, structinfo.VariantStructFI):
					ctx.addAction("Add variant ...", lambda: self.addField(source, "AnyFI"))
					ctx.addSeparator()
				if isinstance(source.fi, structinfo.SwitchFI):
					ctx.addAction("Add case ...", lambda: self.addField(source, "SwitchItem"))
					ctx.addSeparator()
				if parentSource is not None and isinstance(parentSource, structinfo.StructFI):
					ctx.addAction("Remove this field", lambda: self.removeField(parentSource, range.field_name))
					ctx.addSeparator()
				ctx.addAction("Edit ...", lambda: self.editField(source))
				ctx.addAction("Edit tree ...", lambda: self.editField2(source))
				ctx.addAction("Visualization ...", lambda: self.editDisplayParams(source))
				ctx.addAction("Repeat ...", lambda: self.repeatField(source))
				ctx.addSeparator()

		ctx.addAction("New format info ...", self.newFormatInfo)
		ctx.addAction("Load format info ...", self.fileOpenFormatInfo)
		if self.formatInfoContainer and self.formatInfoContainer.file_name:
			ctx.addAction("Save format info", lambda: self.saveFormatInfo(self.formatInfoContainer.file_name))
		ctx.exec(self.mapToGlobal(point))

	def addField(self, parent, typeName):
		def ok(params):
			parent.updateParams(children=parent.params['children']+[params])
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)

		params = showTypeEditorDlg("format_info.tes", typeName, ok_callback=ok)


	def removeField(self, parent, field_name):
		ch = parent.params['children']
		del ch[field_name]
		parent.updateParams(children=ch)
		self.formatInfoUpdated.emit()


	def editDisplayParams(self, parent):
		params = showSettingsDlg([
			("color", "Background color", "color", {"color":True}),
			("textcolor", "Text color", "color", {"color":True}),
			("section", "Section header", "text", {}),
		], title="Edit display params", values=parent.params, parent=self)
		if params is None: return
		if params.get("color") == "": params["color"] = None
		if params.get("textcolor") == "": params["textcolor"] = None
		if params.get("section") == "": params["section"] = None
		parent.updateParams(**params)
		self.formatInfoUpdated.emit()
		self.saveFormatInfo(self.formatInfoContainer.file_name)

	def editField(self, element: structinfo.FormatInfo):
		"""
		params = showTypeEditorDlg("format_info.tes", "AnyFI", element.serialize())
		if params is None: return
		element.deserialize(params)
		"""
		#result, ok = QInputDialog.getMultiLineText(self, "Edit field", "Edit field", element.to_text(0, None))
		#if ok:
		def ok_callback(result):
			element.from_text(result)
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showScintillaDialog(self, "Edit field", element.to_text(0, None), ok_callback=ok_callback)


	def editField2(self, element: structinfo.FormatInfo):
		def ok_callback(params):
			element.deserialize(params)
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showTreeEditorDlg("format_info.tes", "AnyFI", element.serialize(), ok_callback=ok_callback)


	def repeatField(self, element: structinfo.FormatInfo):
		def ok_callback(params):
			element.setContents(structinfo.RepeatStructFI, params)
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)

		showTypeEditorDlg("format_info.tes", "RepeatStructFI", { "children": element.serialize() }, ok_callback=ok_callback)

	def newFormatInfo(self):
		def ok_callback(params):
			fileName, _ = QFileDialog.getSaveFileName(self, "Save format info",
													  configs.getValue(self.optionsConfigKey + "_lastOpenFile", ""),
													  "Format Info files (*.pfi *.txt)")
			if not fileName: return
			self.formatInfoContainer = InteractiveFormatInfoContainer(self, )
			self.formatInfoContainer.main_name = "DEFAULT"
			self.formatInfoContainer.definitions["DEFAULT"] = structinfo.deserialize_fi(params)
			self.formatInfoContainer.file_name = fileName
			self.formatInfoUpdated.emit()
			self.saveFormatInfo(self.formatInfoContainer.file_name)
		showTypeEditorDlg("format_info.tes", "AnyFI", ok_callback=ok_callback)

	def fileOpenFormatInfo(self):
		fileName, _ = QFileDialog.getOpenFileName(self,"Load format info", configs.getValue(self.optionsConfigKey+"_lastOpenFile",""),"Format Info files (*.pfi *.txt)")
		if fileName:
			configs.setValue(self.optionsConfigKey+"_lastOpenFile", fileName)
			self.loadFormatInfo(fileName)

	def loadFormatInfo(self, fileName):
		try:
			self.formatInfoContainer = InteractiveFormatInfoContainer(self, load_from_file=fileName)
		except Exception as ex:
			traceback.print_exc()
			QMessageBox.warning(self, "Failed to parse format info description", str(ex))
			return
		self.formatInfoUpdated.emit()

	def saveFormatInfo(self, fileName):
		self.formatInfoContainer.write_file(fileName)




class HexView2(QWidget):
	on_data_selected = pyqtSignal(QObject)
	onNewSubflowCategory = pyqtSignal(str, object)
	formatInfoUpdated = pyqtSignal()

	SettingsDefinition = [
		('', 'Address', '-', {}),
		('addressFontFamily', 'FontFamily', 'text', {}),
		('addressFontSize', 'FontSize', 'number', {'min':1, 'max':1024}),
		('addressColor', 'Color', 'color', {}),
		('addressFormat', 'Format', 'text', {}),
		('','Hex','-',{}),
		('hexFontFamily', 'FontFamily', 'text', {}),
		('hexFontSize', 'FontSize', 'number', {'min':1, 'max':1024}),
		('hexColor', 'Color', 'color', {}),
		('hexSpaceAfter', 'SpaceAfter', 'number', {'min':1, 'max':1024}),
		('hexSpaceWidth', 'SpaceWidth', 'number', {'min':1, 'max':1024}),
		('','ASCII','-',{}),
		('asciiFontFamily', 'FontFamily', 'text', {}),
		('asciiFontSize', 'FontSize', 'number', {'min':1, 'max':1024}),
		('asciiColor', 'Color', 'color', {}),
		('','Section','-',{}),
		('sectionFontFamily', 'FontFamily', 'text', {}),
		('sectionFontSize', 'FontSize', 'number', {'min':1, 'max':1024}),
		('sectionColor', 'Color', 'color', {}),
		('','','-',{}),
		('lineHeight', 'lineHeight', 'number', {'min':0.1, 'max':10}),
		('bytesPerLine', 'bytesPerLine', 'number', {'min':1, 'max':1024}),
	]
	def __init__(self, byteBuffer=None, options=dict(), optionsConfigKey="HexViewParams"):
		super().__init__()
		self.buffers = list()
		self.firstLine = 0
		self.scrollY = 0
		self.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.fiTreeWidget = RangeTreeWidget(self)
		self.fiTreeWidget.show()
		self.fiTreeWidget.currentItemChanged.connect(self.fiTreeItemSelected)
		self.fiTreeWidget.formatInfoUpdated.connect(self.applyFormatInfo)
		self.backgroundPixmap = QPixmap()
		self.textPixmap = QPixmap()

		self.options = {
			'addressFontFamily': 'monospace', 'addressFontSize': 10, 'addressColor': '#888888',
			'hexFontFamily': 'monospace', 'hexFontSize': 10, 'hexColor': '#ffffff',
			'asciiFontFamily': 'monospace', 'asciiFontSize': 10, 'asciiColor': '#bbffbb',
			'sectionFontFamily': 'Serif', 'sectionFontSize': 8, 'sectionColor': '#aaaaaa',
			'lineHeight': 1.1,
			'addressFormat': '{:08x}',
			'bytesPerLine': 16,
			'hexSpaceAfter': 8, 'hexSpaceWidth': 8
		}
		self.optionsConfigKey = optionsConfigKey
		if optionsConfigKey is not None:
			self.setOptions(configs.getValue(optionsConfigKey, {}))
		self.setOptions(options)

		self.selBuffer = 0
		self.selStart = 0
		self.selEnd = 0
		self.itemY = list()
		self.lastHit = None
		self.selecting = False
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		if byteBuffer == None:
			self.setBytes(bytes())
		else:
			self.setBuffer(byteBuffer)
		self.setMouseTracking(True)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)



	def setOptions(self, options):
		self.options.update(options)

		self.bytesPerLine = self.options['bytesPerLine']
		self.addressFormat = self.options['addressFormat']

		self.xAddress = 5
		self.fontAddress = QFont(self.options['addressFontFamily'], self.options['addressFontSize'], QFont.Light)
		self.fsAddress = QColor(self.options['addressColor'])

		self.xHex = QFontMetrics(self.fontAddress).width(self.addressFormat.format(0)) + 15
		self.fontHex = QFont(self.options['hexFontFamily'], self.options['hexFontSize'], QFont.Light)
		self.fsHex = QColor(self.options['hexColor']);	self.dxHex = QFontMetrics(self.fontHex).width("00")+4
		self.hexSpaceAfter = self.options['hexSpaceAfter']; self.hexSpaceWidth = self.options['hexSpaceWidth']

		self.xAscii = self.xHex + self.dxHex*self.bytesPerLine+(ceil(self.bytesPerLine/self.hexSpaceAfter)-1)*self.hexSpaceWidth+15
		self.fontAscii = QFont(self.options['asciiFontFamily'], self.options['asciiFontSize'], QFont.Light)
		self.fsAscii = QColor(self.options['asciiColor']); self.dxAscii = QFontMetrics(self.fontAscii).width("W")

		self.fsSel = QColor("#7fff9bff");  self.fsHover = QColor("#7f9b9bff")
		self.fontSection = QFont(self.options['sectionFontFamily'], self.options['sectionFontSize'], QFont.Light)
		self.fsSection = QColor(self.options['sectionColor']);

		self.dyLine = max(QFontMetrics(self.fontAddress).height(), QFontMetrics(self.fontHex).height()) * self.options['lineHeight']

		self.fiTreeWidget.move(self.xAscii + self.dxAscii*self.bytesPerLine + 10, 10)
		self.redraw()

	def showParamDialog(self):
		result = showSettingsDlg(HexView2.SettingsDefinition, self.options)
		if result is not None:
			self.setOptions(result)
			self.storeOptions()



	def storeOptions(self):
		if self.optionsConfigKey is not None:
			configs.setValue(self.optionsConfigKey, self.options)


	############ HEX VIEW CONTEXT MENU  #############################################################

	def onCustomContextMenuRequested(self, point):
		hit = self.hitTest(point)
		ctxMenu = None
		ctxMenu = QMenu("Context menu", self)
		if hit != None:
			if hit < self.selStart or hit > self.selEnd:
				self.selStart = self.selEnd = hit
				self.selecting = False
				self.redrawSelection()
			self.buildSelectionContextMenu(ctxMenu)
		else:
			self.buildGeneralContextMenu(ctxMenu)
		ctxMenu.exec(self.mapToGlobal(point))

	def buildSelectionContextMenu(self, ctx):
		ctx.addAction(QAction("Copy selection hex\tCtrl-C", ctx, triggered=lambda: self.copySelection(), shortcut="Ctrl+C"))
		ctx.addAction("Copy selection C Array", lambda: self.copySelection((", ", "0x%02X")))
		ctx.addAction("Copy selection hexdump\tCtrl-Shift-C", lambda: self.copySelection("hexdump"))
		ctx.addSeparator()
		ctx.addAction("Selection %d-%d (%d bytes)"%(self.selStart,self.selEnd,self.selLength()))
		ctx.addAction("Selection 0x%X - 0x%X (0x%X bytes)"%(self.selStart,self.selEnd,self.selLength()))
		ctx.addAction("Red", lambda: self.styleSelection(color="#aa0000"))
		ctx.addAction("Green", lambda: self.styleSelection(color="#00aa00"))
		ctx.addAction("Yellow", lambda: self.styleSelection(color="#aaaa00"))
		ctx.addAction("Blue", lambda: self.styleSelection(color="#0000aa"))
		ctx.addSeparator()
		for d in self.buffers[0].matchRanges(overlaps=self.selRange()):
			ctx.addAction("Range %d-%d (%s): %s" % (d.start, d.end, d.metadata.get("name"), d.metadata.get("showname")), lambda d=d: self.selectRange(d))
			for k,v in d.metadata.items():
				if k != "name" and k != "showname":
					ctx.addAction("    %s=%s" % (k,str_ellipsis(str(v),75)))


	def buildGeneralContextMenu(self, ctx):
		ctx.addAction("Select all", lambda: self.selectAll())
		ctx.addAction("Options ...", self.showParamDialog)
		ctx.addAction("Paste", lambda: self.setBuffer(parseHexFromClipboard()))
		ctx.addAction("Clear ranges", lambda: self.clearRanges())


	def clearRanges(self):
		self.buffers[0].clearRanges()
		self.redraw()

	def getRangeString(self, range, style=(" ","%02X")):
		if isinstance(style, tuple):
			return self.buffers[0].toHex(range.start, range.length(), " ", "%02X")
		elif style=="hexdump":
			return self.buffers[0].toHexDump(range.start, range.length())

	def copySelection(self, style=(" ","%02X")):
		setClipboardText(self.getRangeString(self.selRange(), style))

	def styleSelection(self, **kw):
		selr = self.selRange()
		match = self.buffers[0].matchRanges(start=selr.start, end=selr.end)
		if len(match) > 0:
			match[0].style.update(kw)
		else:
			selr.style.update(kw)
			self.buffers[0].addRange(selr)



	################# FI Tree ####################################################

	def applyFormatInfo(self):
		if self.fiTreeWidget.formatInfoContainer != None:
			# TODO clear out the old ranges from the last run, but don't delete ranges from other sources (e.g. style, bidi-buf)
			try:
				self.formatInfoUpdated.emit()
				parse_context = structinfo.BytebufferAnnotatingParseContext(self.fiTreeWidget.formatInfoContainer, self.buffers[0])
				parse_context.on_new_subflow_category = self.newSubflowCategory
				self.buffers[0].fi_tree = parse_context.parse()
				self.fiTreeWidget.updateTree(self.buffers[0])
				self.redraw()
			except structinfo.parse_exception as ex:
				traceback.print_exc()
				QMessageBox.warning(self, "Failed to apply format info", str(ex))


	def newSubflowCategory(self, category, parse_context, **kv):
		print("on_new_subflow_category",category)
		self.onNewSubflowCategory.emit(category, parse_context)


	def fiTreeItemSelected(self, item, previous):
		if item == None: return
		range = item.data(0, Range.RangeRole)
		if range != None:
			self.selectRange(range, scrollIntoView=True)
		#source = item.data(0, Range.SourceDescRole)
		#if isinstance(source, structinfo.AbstractFI):
			#self.on_data_selected.emit(source)



	#############  SCROLLING  ###########################################

	def wheelEvent(self, e):
		if e.pixelDelta().isNull():
			deltaY = e.angleDelta().y() / 4
		else:
			deltaY = e.pixelDelta().y()
		if deltaY == 0: return
		self.scrollY = max(0, min((self.maxLine()-1)*self.dyLine, self.scrollY - deltaY))
		self.firstLine = ceil(self.scrollY / self.dyLine)
		print("wheel",deltaY,self.scrollY)
		self.redraw()

	def scrollIntoView(self, offset):
		line = floor(offset / self.bytesPerLine)
		if line < self.firstLine:
			self.setFirstLine(line - 2)
		elif line >= self.maxVisibleLine():
			self.setFirstLine(line - 5)  #TODO - ich weiß vorher nicht, wie viele zeilen auf den schirm passen

	def setFirstLine(self, line):
		self.firstLine = max(0, min(self.maxLine()-1, line))
		self.scrollY = self.firstLine * self.dyLine
		self.redraw()

	############## MOUSE EVENTS - SELECTION  ############################

	def mouseMoveEvent(self, e):
		hit = self.hitTest(e.pos())
		if (hit == self.lastHit): return
		self.lastHit = hit
		if (self.selecting and hit != None): self.selEnd = hit
		self.redrawSelection()

	def mousePressEvent(self, e):
		if e.button() != Qt.LeftButton: return
		hit = self.hitTest(e.pos())
		if (hit == None): return
		self.lastHit = hit
		self.selStart = self.selEnd = hit
		self.selecting = True
		self.redrawSelection()
		
	def mouseReleaseEvent(self, e):
		if e.button() != Qt.LeftButton: return
		self.selecting = False
		self.select(self.selStart, self.selEnd)
		print("selection changed",self.selStart, self.selEnd, self.lastHit)

	def hitTest(self, point):
		x, y = point.x(), point.y()
		linePos = None
		if (x >= self.xAscii):
			pos = floor((x - self.xAscii) / self.dxAscii);
			if (pos < self.bytesPerLine): linePos = pos; #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}
		elif (x >= self.xHex):
			xx = (x - self.xHex)
			xx -= floor(xx / (self.dxHex*self.hexSpaceAfter + self.hexSpaceWidth)) * self.hexSpaceWidth # correction factor for hex grouping
			pos = floor(xx / self.dxHex);
			if (pos < self.bytesPerLine): linePos = pos; #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}

		#//console.log(x,y,linePos);
		if (linePos is None): return None

		for i in range(linePos, len(self.itemY), self.bytesPerLine):
			#//console.log(i,self.itemY[i],y,self.itemY[i] <= y , y <= self.itemY[i]+self.dyLine)
			if (self.itemY[i] <= y and y <= self.itemY[i]+self.dyLine):
				return self.lineNumberToByteOffset(self.firstLine) + i;

		return None


	def selFirst(self):
		return min(self.selStart, self.selEnd)
	def selLength(self):
		return max(self.selStart, self.selEnd) - self.selFirst() + 1
	def selRange(self):
		return Range(min(self.selStart,self.selEnd), max(self.selStart,self.selEnd)+1, buffer_idx=self.selBuffer)

	def clipPosition(self, bufferIdx, pos):
		return max(0, min(len(self.buffers[bufferIdx]), pos))

	def select(self, start:int, end:int, bufferIdx=0, scrollIntoView=False):
		#TODO ensure that start, end are in valid range
		self.selStart = self.clipPosition(bufferIdx, start); self.selEnd = self.clipPosition(bufferIdx, end)
		self.selBuffer = bufferIdx
		if scrollIntoView:
			self.scrollIntoView(self.selEnd)
			self.scrollIntoView(self.selStart)

		self.redrawSelection()
		print("selection changed",self.selStart, self.selEnd, self.lastHit)
		self.fiTreeWidget.hilightFormatInfoTree(self.selRange())
		QApplication.postEvent(self, QStatusTipEvent("Selection %d-%d (%d bytes)   0x%X - 0x%X (0x%X bytes)"%(
			self.selStart,self.selEnd,self.selLength(),self.selStart,self.selEnd,self.selLength())))


	def selectRange(self, rangeObj, scrollIntoView=False):
		self.select(rangeObj.start, max(rangeObj.start, rangeObj.end-1), bufferIdx=rangeObj.buffer_idx, scrollIntoView=scrollIntoView)

	def selectAll(self):
		self.select(0, len(self.buffers[0]))



	######## KEYBOARD EVENTS ###########################################

	def keyPressEvent(self, e: QKeyEvent) -> None:
		mod = e.modifiers() & ~QtCore.Qt.KeypadModifier

		arrow = None
		if e.key() == QtCore.Qt.Key_Left:
			arrow = self.selEnd - 1
		elif e.key() == QtCore.Qt.Key_Right:
			arrow = self.selEnd + 1
		elif e.key() == QtCore.Qt.Key_Up:
			arrow = self.selEnd - self.bytesPerLine
		elif e.key() == QtCore.Qt.Key_Down:
			arrow = self.selEnd + self.bytesPerLine

		#print("hexView Key Press %d 0x%x %d"%(e.key(), int(e.modifiers()), arrow))
		if arrow and mod == QtCore.Qt.ShiftModifier:
			self.select(self.selStart, arrow)
		elif arrow and mod == QtCore.Qt.NoModifier:
			self.select(arrow, arrow)

		if mod == QtCore.Qt.ControlModifier:
			if e.key() == QtCore.Qt.Key_A:
				self.selectAll()
			elif e.key() == QtCore.Qt.Key_C:
				self.copySelection()
			elif e.key() == QtCore.Qt.Key_I:
				self.fiTreeWidget.loadFormatInfo(configs.getValue(self.fiTreeWidget.optionsConfigKey+"_lastOpenFile",""))
			elif e.key() == QtCore.Qt.Key_F5:
				self.applyFormatInfo()
			elif e.key() == QtCore.Qt.Key_Plus:
				self.options['addressFontSize'] += 1
				self.options['hexFontSize'] += 1
				self.options['asciiFontSize'] += 1
				self.options['sectionFontSize'] += 1
				self.setOptions({}); self.storeOptions()
			elif e.key() == QtCore.Qt.Key_Minus:
				self.options['addressFontSize'] -= 1
				self.options['hexFontSize'] -= 1
				self.options['asciiFontSize'] -= 1
				self.options['sectionFontSize'] -= 1
				self.setOptions({}); self.storeOptions()
			elif e.key() == QtCore.Qt.Key_0:
				self.options['addressFontSize'] = 10
				self.options['hexFontSize'] = 10
				self.options['asciiFontSize'] = 10
				self.options['sectionFontSize'] = 8
				self.setOptions({}); self.storeOptions()

		if mod == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier:
			if e.key() == QtCore.Qt.Key_C:
				self.copySelection("hexdump")
			elif e.key() == QtCore.Qt.Key_I:
				self.fiTreeWidget.fileOpenFormatInfo()


	#################  data setters   ##########################################
	def setBytes(self, buf : bytes):
		#abuf = ByteBuffer();
		#abuf.setBytes(0, buf, undefined, undefined);
		abuf = ByteBuffer(buf)
		self.buffers = [ abuf ];
		self.firstLine = 0;
		self.redraw();
	
	def setBuffer(self, bbuf):
		if isinstance(bbuf, BidiByteBuffer):
			self.buffers = bbuf.buffers
		elif isinstance(bbuf, ByteBuffer):
			self.buffers = [ bbuf ];
		else:
			raise TypeError("Invalid type passed to HexView2.setBuffer: "+str(type(bbuf)))
		self.firstLine = 0;
		self.redraw()
		if self.fiTreeWidget.formatInfoContainer is None:
			self.fiTreeWidget.formatInfoContainer = bbuf.fi_container
		self.fiTreeWidget.updateTree(self.buffers[0])
		if self.buffers[0].fi_tree == None: self.applyFormatInfo()

	############ RENDERING ############################################################

	def resizeEvent(self, e):
		self.redraw();
		self.fiTreeWidget.resize(self.width() - self.fiTreeWidget.pos().x()-10, self.height()-20)

	def sizeHint(self):
		return QSize(self.xAscii + self.dxAscii * self.bytesPerLine + 10, 256)

	def redraw(self):
		if self.size().height() < 3 or self.size().width() < 3: return
		if self.size() != self.backgroundPixmap.size():
			self.backgroundPixmap = QPixmap(self.size())
			self.textPixmap = QPixmap(self.size())
		self.backgroundPixmap.fill(QColor("#333333"))
		self.textPixmap.fill(QColor("#00000000"))

		qpBg = QPainter()
		qpBg.begin(self.backgroundPixmap)
		qpTxt = QPainter()
		qpTxt.begin(self.textPixmap)
		self.drawLines(qpTxt, qpBg)
		qpBg.end()
		qpTxt.end()
		self.repaint()

	def redrawSelection(self):
		self.repaint()

	def paintEvent(self, e):
		qp = QPainter()
		qp.begin(self)
		qp.drawPixmap(0, 0, self.backgroundPixmap)
		self.drawSelection(qp)
		self.drawHover(qp)
		qp.drawPixmap(0, 0, self.textPixmap)
		#self.drawQuicktip(qp)
		qp.end()

	def drawLines(self, qpTxt, qpBg):
		y=10
		canvasHeight = self.size().height()
		if len(self.buffers) == 0: return
		buffer = self.buffers[0]
		maxLine = self.maxLine()
		self.itemY = list()
		lineNumber = self.firstLine
		while y < canvasHeight and lineNumber < maxLine:
			y = self.drawLine(qpTxt, qpBg, lineNumber, y, buffer)
			lineNumber+=1
	
	def drawLine(self, qpTxt, qpBg, lineNumber, y, buffer):
		TXT_DY = 14
		offset = self.lineNumberToByteOffset(lineNumber)
		end = min(len(buffer), offset + self.bytesPerLine)
		ii = 0
		lastSection=[]
		for i in range(offset, end):
			theByte = buffer.getByte(i)

			#// if specified, print section header
			sectionAnnotations = buffer.getAnnotationValues(start=i, annotationProperty="section");
			if len(sectionAnnotations) != 0:
				if (ii != 0): y += self.dyLine;
				qpTxt.setFont(self.fontSection)
				qpTxt.setPen(self.fsSection);
				for row in sectionAnnotations:
					qpTxt.drawText(5, y+TXT_DY, row)
					y += self.dyLine;
				qpTxt.setFont(self.fontAddress)
				qpTxt.setPen(QColor("#555555"));
				if (ii != 0): qpTxt.drawText(self.xAddress, y+TXT_DY, self.addressFormat.format(i));
			
			
			if (ii == 0):  #//print address for first byte in line
				qpTxt.setFont(self.fontAddress)
				qpTxt.setPen(self.fsAddress);
				qpTxt.drawText(self.xAddress, y+TXT_DY, self.addressFormat.format(offset));
			

			#// if specified, draw background color from style attribute
			bg = buffer.getStyle(i, "color", None);
			fg = buffer.getStyle(i, "textcolor", None);
			if (bg):
				qpBg.fillRect(self.xHex + ii * self.dxHex + int(ii/self.hexSpaceAfter)*self.hexSpaceWidth + 2, y+1, self.dxHex, self.dyLine-2, QColor(bg))
				qpBg.fillRect(self.xAscii + ii * self.dxAscii, y+1, self.dxAscii, self.dyLine-2, QColor(bg))
			

			#// store item's Y position
			self.itemY.append(y)

			#// print HEX and ASCII representation of this byte
			qpTxt.setFont(self.fontHex)
			qpTxt.setPen( self.fsHex if fg is None else QColor(fg))
			qpTxt.drawText(self.xHex + ii * self.dxHex + int(ii/self.hexSpaceAfter)*self.hexSpaceWidth + 2, y+TXT_DY, "%02x"%(theByte));
			qpTxt.setFont(self.fontAscii)
			qpTxt.setPen(self.fsAscii if fg is None else QColor(fg))
			asciichar = chr(theByte) if (theByte > 0x20 and theByte < 0x80) else "."
			qpTxt.drawText(self.xAscii + ii * self.dxAscii, y+TXT_DY, asciichar);
			ii += 1
		return y + self.dyLine

	def drawSelection(self, qp):
		selMin = min(self.selStart, self.selEnd)
		selMax = max(self.selStart, self.selEnd)
		for i in range(selMin, selMax+1):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(i)
			qp.fillRect(xHex, y, self.dxHex, dy, self.fsSel)
			qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsSel)

		for selHelper in selectionHelpers:
			selHelper(self, qp, self.buffers[0], (selMin, selMax))

	def drawHover(self, qp):
		if (self.lastHit != None):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(self.lastHit)
			qp.fillRect(xHex, y, self.dxHex, dy, self.fsHover)
			qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsHover)

	########### CALCULATION    #########################
	def lineNumberToByteOffset(self, lineNumber:int):
		return lineNumber * self.bytesPerLine;

	def maxLine(self):
		return ceil(len(self.buffers[0]) / self.bytesPerLine);

	def maxVisibleLine(self):
		return self.firstLine + ceil(len(self.itemY)/self.bytesPerLine)

	def offsetToClientPos(self, offset):
		pos = offset % self.bytesPerLine
		visibleIdx = offset - self.bytesPerLine*self.firstLine
		if visibleIdx < 0 or visibleIdx >= len(self.itemY): return (0,0,0,0)
		y = self.itemY[visibleIdx]
		return (self.xHex + pos * self.dxHex + int(pos/self.hexSpaceAfter)*self.hexSpaceWidth, self.xAscii + self.dxAscii*pos,y,self.dyLine)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	ex = HexView2()
	ex.show()
	ex.setBytes(open(sys.argv[1], "rb").read())
	sys.exit(app.exec_())

