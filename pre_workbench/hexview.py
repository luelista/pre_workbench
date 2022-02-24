#!/usr/bin/python3
# -*- coding: utf-8 -*-
# PRE Workbench
# Copyright (C) 2022 Mira Weller
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
import json
import logging
import re
import sys
from math import ceil, floor

from PyQt5 import QtCore
from PyQt5.QtCore import (Qt, QSize, pyqtSignal)
from PyQt5.QtGui import QPainter, QFont, QColor, QPixmap, QFontMetrics, QKeyEvent, QStatusTipEvent, QMouseEvent
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSizePolicy, QAction, QInputDialog, QComboBox
from pre_workbench.algo.rangelist import Range

from pre_workbench import configs, guihelper
from pre_workbench.configs import SettingsSection
from pre_workbench.guihelper import setClipboardText, GlobalEvents, showWidgetDlg
from pre_workbench.hexview_selheur import SelectionHelpers
from pre_workbench.objects import ByteBuffer, parseHexFromClipboard, BidiByteBuffer
from pre_workbench.rangetree import RangeTreeWidget
from pre_workbench.structinfo.exceptions import parse_exception
from pre_workbench.structinfo.parsecontext import BytebufferAnnotatingParseContext
from pre_workbench.util import PerfTimer

group = SettingsSection('HexView2', 'Hex Editor', 'address', 'Address Styles')
configs.registerOption(group, 'Color', 'Address Color', 'color', {}, '#888888',None)
configs.registerOption(group, 'Format', 'Address Format', 'text', {}, '{:08x}',None)

group = SettingsSection('HexView2', 'Hex Editor', 'hex', 'Hex Styles')
configs.registerOption(group, 'Font', 'Font', 'font', {}, 'Courier, 10',None)
configs.registerOption(group, 'Color', 'Hex Color', 'color', {}, '#ffffff', None)
configs.registerOption(group, 'SpaceAfter', 'Hex SpaceAfter', 'int', {'min': 1, 'max': 1024}, 8, None)
configs.registerOption(group, 'SpaceWidth', 'Hex SpaceWidth', 'int', {'min': 1, 'max': 1024}, 8, None)
configs.registerOption(group, 'Format', 'Hex Format', 'select', {'options':[
	('{:02x}', "Hexadecimal"),
	('{:08b}', "Binary"),
	('{:04o}', "Octal"),
	('{:03d}', "Decimal"),
]}, '{:02x}', None)

group = SettingsSection('HexView2', 'Hex Editor', 'ascii', 'ASCII Styles')
configs.registerOption(group, 'Color', 'ASCII Color', 'color', {}, '#bbffbb', None)

group = SettingsSection('HexView2', 'Hex Editor', 'section', 'Section Styles')
configs.registerOption(group, 'Font', 'Font', 'font', {}, 'Arial, 10',None)
configs.registerOption(group, 'Color', 'Section Color', 'color', {}, '#aaaaaa', None)

group = SettingsSection('HexView2', 'Hex Editor', 'general', 'General')
configs.registerOption(group, 'lineHeight', 'lineHeight', 'double', {'min': 0.1, 'max': 10}, 1.3, None)
configs.registerOption(group, 'bytesPerLine', 'bytesPerLine', 'int', {'min': 1, 'max': 1024}, 16, None)

pattern_heading = re.compile("[#]{0,6}")

class HexView2(QWidget):
	onNewSubflowCategory = pyqtSignal(str, object)
	formatInfoUpdated = pyqtSignal()
	selectionChanged = pyqtSignal(object)

	userStyles = [
		("R", "Red", {"color": "#aa0000"}),
		("G", "Green", {"color": "#00aa00"}),
		("Y", "Yellow", {"color": "#aaaa00"}),
		("L", "Blue", {"color": "#0000aa"}),
		("M", "Magenta", {"color": "#aa00aa"}),
		("T", "Turqoise", {"color": "#00aaaa"}),
	]

	def __init__(self, byteBuffer=None, annotationDefaultName="", options=dict(), optionsConfigKey="HexViewParams"):
		super().__init__()
		self.annotationDefaultName = annotationDefaultName
		self.buffers = list()
		self.firstLine = 0
		self.scrollY = 0
		self.partialLineScrollY = 0
		self.setFocusPolicy(QtCore.Qt.StrongFocus)

		self.initUI()

		self.backgroundPixmap = QPixmap()
		self.textPixmap = QPixmap()
		GlobalEvents.on_config_change.connect(self.loadOptions)
		self.loadOptions()

		self.pixmapsInvalid = True
		self.selBuffer = 0
		self.selStart = 0
		self.selEnd = 0
		self.itemY = list()
		self.lastHit = None
		self.selecting = False
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		if byteBuffer is None:
			self.setBytes(bytes())
		else:
			self.setBuffer(byteBuffer)
		self.setMouseTracking(True)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

	def initUI(self):
		self.fiTreeWidget = RangeTreeWidget(self)
		self.fiTreeWidget.show()
		self.fiTreeWidget.currentItemChanged.connect(self.fiTreeItemSelected)
		self.fiTreeWidget.formatInfoUpdated.connect(self.applyFormatInfo)

		self.annotationSelect = QComboBox(self)
		self.annotationSelect.show()
		self.annotationSelect.addItems([self.annotationDefaultName] + guihelper.CurrentProject.getAnnotationSetNames())
		self.annotationSelect.currentTextChanged.connect(self.loadAnnotations)
		#self.loadAnnotations(self.annotationDefaultName)
		self.fiSelect = QComboBox(self)
		self.fiSelect.show()

	def loadOptions(self, *dummy):
		self.bytesPerLine = configs.getValue('HexView2.general.bytesPerLine')
		self.addressFormat = configs.getValue('HexView2.address.Format')
		self.hexFormat = configs.getValue('HexView2.hex.Format')

		self.fontAddress = self.fontHex = self.fontAscii = QFont()
		self.fontHex.fromString(configs.getValue('HexView2.hex.Font'))

		self.xAddress = 5
		#self.fontAddress = QFont()
		#self.fontAddress.fromString(configs.getValue('HexView2.address.Font'))
		self.fsAddress = QColor(configs.getValue('HexView2.address.Color'))

		self.xHex = QFontMetrics(self.fontAddress).width(self.addressFormat.format(0)) + 15
		#self.fontHex = QFont()
		#self.fontHex.fromString(configs.getValue('HexView2.hex.Font'))
		self.fsHex = QColor(configs.getValue('HexView2.hex.Color'));	self.dxHex = QFontMetrics(self.fontHex).width(self.hexFormat.format(0))+4
		self.hexSpaceAfter = configs.getValue('HexView2.hex.SpaceAfter'); self.hexSpaceWidth = configs.getValue('HexView2.hex.SpaceWidth')

		self.xAscii = self.xHex + self.dxHex*self.bytesPerLine+(ceil(self.bytesPerLine/self.hexSpaceAfter)-1)*self.hexSpaceWidth+15
		#self.fontAscii = QFont()
		#self.fontAscii.fromString(configs.getValue('HexView2.ascii.Font'))
		self.fsAscii = QColor(configs.getValue('HexView2.ascii.Color')); self.dxAscii = QFontMetrics(self.fontAscii).width("W")

		self.fsSel = QColor("#7fff9bff");  self.fsHover = QColor("#7f9b9bff")
		sectionFont = QFont(); sectionFont.fromString(configs.getValue('HexView2.section.Font'))
		self.fontSection = []
		for i in [0,10,8,6,4,2]:
			f = QFont(sectionFont)
			f.setPointSize(f.pointSize() + i)
			self.fontSection.append(f)
		self.fsSection = QColor(configs.getValue('HexView2.section.Color'));

		self.charHeight = QFontMetrics(self.fontHex).height()
		self.dyLine = ceil(self.charHeight * configs.getValue('HexView2.general.lineHeight'))
		self.fontAscent = ceil(QFontMetrics(self.fontHex).ascent())
		self.linePadding = ceil(max(0, self.charHeight * (configs.getValue('HexView2.general.lineHeight') - 1) / 2))
		print(self.charHeight, self.dyLine, self.fontAscent, self.linePadding)

		self.fiTreeWidget.move(self.xAscii + self.dxAscii*self.bytesPerLine + 10, 10)
		self.redraw()


	############ HEX VIEW CONTEXT MENU  #############################################################

	def onCustomContextMenuRequested(self, point):
		hit = self.hitTest(point)
		ctxMenu = QMenu("Context menu", self)
		if hit is not None:
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
		#ctx.addAction("Copy selected annotations", lambda: self.copySelection("hexdump"))
		ctx.addSeparator()
		#ctx.addAction("Selection %d-%d (%d bytes)"%(self.selStart,self.selEnd,self.selLength()))
		#ctx.addAction("Selection 0x%X - 0x%X (0x%X bytes)"%(self.selStart,self.selEnd,self.selLength()))
		try:
			match = next(
				self.buffers[0].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))

			ctx.addAction("&Delete selected style\tX", lambda: self.deleteSelectedStyle())

			ctx.addSeparator()
		except StopIteration:
			pass
		for key, name, style in HexView2.userStyles:
			ctx.addAction(name+"\t"+key, lambda: self.styleSelection(**style))
		ctx.addSeparator()
		ctx.addAction("&Start Section...", lambda: self.setSectionSelection())
		ctx.addSeparator()


	def buildGeneralContextMenu(self, ctx):
		ctx.addAction("Select all", lambda: self.selectAll())
		ctx.addSeparator()
		ctx.addAction("Paste", lambda: self.setBuffer(parseHexFromClipboard()))
		ctx.addAction("Clear ranges", lambda: self.clearRanges())


	def setDefaultAnnotationSet(self, name):
		self.annotationDefaultName = name
		self.annotationSelect.setItemText(0, name)
		self.loadAnnotations(name)

	def loadAnnotations(self, set_name):
		self.buffers[0].setRanges(self.buffers[0].matchRanges(hasMetaKey='_sdef_ref'))
		annotations = guihelper.CurrentProject.getAnnotations(set_name)
		for rowid, start, end, meta_str in annotations:
			meta = json.loads(meta_str)
			if meta.get("deleted"): continue
			meta['rowid'] = rowid
			self.buffers[0].addRange(Range(start=start, end=end, meta=meta))
		self.redraw()

	def storeAnnotaton(self, range):
		if not self.annotationSelect.currentText(): return
		guihelper.CurrentProject.storeAnnotation(self.annotationSelect.currentText(), range)


	def clearRanges(self):
		self.buffers[0].clearRanges()
		self.redraw()

	def getRangeString(self, range, style=(" ","%02X")):
		if isinstance(style, tuple):
			return self.buffers[0].toHex(range.start, range.length(), style[0], style[1])
		elif style=="hexdump":
			return self.buffers[0].toHexDump(range.start, range.length())

	def copySelection(self, style=(" ","%02X")):
		setClipboardText(self.getRangeString(self.selRange(), style))

	def styleSelection(self, **kw):
		selection = self.selRange()
		try:
			match = next(self.buffers[0].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))
		except StopIteration:
			match = selection
			self.buffers[0].addRange(selection)

		match.metadata.update(kw)
		self.storeAnnotaton(match)
		self.redraw()

	def setSectionSelection(self):
		selection = self.selRange()
		try:
			match = next(self.buffers[0].matchRanges(start=selection.start, doesntHaveMetaKey='_sdef_ref'))
			title = match.metadata.get("section")
		except StopIteration:
			match = None
			title = ""

		newTitle, ok = QInputDialog.getText(self, "Section", "Enter section title:", text=title)
		if ok:
			if match is None:
				match = selection
				self.buffers[0].addRange(selection)
			match.metadata.update(section=newTitle)
			self.storeAnnotaton(match)
			self.redraw()

	def deleteSelectedStyle(self):
		try:
			match = next(
				self.buffers[0].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))
			self.buffers[0].removeRange(match)
			match.metadata["deleted"] = True
			self.storeAnnotaton(match)
			self.redraw()
		except StopIteration:
			pass


	################# FI Tree ####################################################

	def applyFormatInfo(self):
		if self.fiTreeWidget.formatInfoContainer != None:
			try:
				self.formatInfoUpdated.emit()

				# clear out the old ranges from the last run, but don't delete ranges from other sources (e.g. style, bidi-buf)
				self.buffers[0].setRanges(self.buffers[0].matchRanges(doesntHaveMetaKey='_sdef_ref'))

				parse_context = BytebufferAnnotatingParseContext(self.fiTreeWidget.formatInfoContainer, self.buffers[0])
				parse_context.on_new_subflow_category = self.newSubflowCategory
				self.buffers[0].fi_tree = parse_context.parse()
				self.fiTreeWidget.updateTree(self.buffers[0].fi_tree)
				self.redraw()
			except parse_exception as ex:
				logging.exception("Failed to apply format info")
				logging.getLogger("DataSource").error("Failed to apply format info: "+str(ex))
				#QMessageBox.warning(self, "Failed to apply format info", str(ex))


	def newSubflowCategory(self, category, parse_context, **kv):
		print("on_new_subflow_category",category)
		self.onNewSubflowCategory.emit(category, parse_context)


	def fiTreeItemSelected(self, item, previous):
		if item is None: return
		range = item.data(0, Range.RangeRole)
		if range is not None:
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
		self.firstLine = floor(self.scrollY / self.dyLine)
		self.partialLineScrollY = self.scrollY - (self.dyLine * self.firstLine)
		logging.debug("wheelEvent deltaY=%d scrollY=%d partial=%d",deltaY,self.scrollY,self.partialLineScrollY)
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

	def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
		if e.button() != Qt.LeftButton: return

		try:
			match = next(self.buffers[0].matchRanges(contains=self.selFirst(), doesntHaveMetaKey='_sdef_ref'))
			self.select(match.start, match.end-1)
		except StopIteration:
			pass

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
	def selLast(self):
		return max(self.selStart, self.selEnd)
	def selLength(self):
		return max(self.selStart, self.selEnd) - self.selFirst() + 1
	def selRange(self):
		return Range(min(self.selStart,self.selEnd), max(self.selStart,self.selEnd)+1, buffer_idx=self.selBuffer)

	def clipPosition(self, bufferIdx, pos):
		return max(0, min(len(self.buffers[bufferIdx]) - 1, pos))

	def select(self, start:int, end:int, bufferIdx=0, scrollIntoView=False):
		#TODO ensure that start, end are in valid range
		self.selStart = self.clipPosition(bufferIdx, start); self.selEnd = self.clipPosition(bufferIdx, end)
		self.selBuffer = bufferIdx
		if scrollIntoView:
			self.scrollIntoView(self.selEnd)
			self.scrollIntoView(self.selStart)

		self.redrawSelection()
		logging.debug("selection changed %r-%r (%r)",self.selStart, self.selEnd, self.lastHit)
		r = self.selRange()

		self.fiTreeWidget.hilightFormatInfoTree(r)

		with PerfTimer("selectionChanged event handlers"):
			self.selectionChanged.emit(r)

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
		if arrow is not None and mod == QtCore.Qt.ShiftModifier:
			self.select(self.selStart, arrow)
		elif arrow is not None and mod == QtCore.Qt.NoModifier:
			self.select(arrow, arrow)

		if mod == QtCore.Qt.ControlModifier:
			if e.key() == QtCore.Qt.Key_A:
				self.selectAll()
			elif e.key() == QtCore.Qt.Key_C:
				self.copySelection()
			elif e.key() == QtCore.Qt.Key_I:
				self.fiTreeWidget.loadFormatInfo(load_from_file=configs.getValue(self.fiTreeWidget.optionsConfigKey+"_lastOpenFile",""))
			elif e.key() == QtCore.Qt.Key_F5:
				self.applyFormatInfo()
			elif e.key() == QtCore.Qt.Key_Plus:
				self.fontHex.setPointSize(self.fontHex.pointSize() + 1)
				configs.setValue('HexView2.hex.Font', self.fontHex.toString())
			elif e.key() == QtCore.Qt.Key_Minus:
				self.fontHex.setPointSize(self.fontHex.pointSize() - 1)
				configs.setValue('HexView2.hex.Font', self.fontHex.toString())

			elif e.key() == QtCore.Qt.Key_0:
				self.fontHex.setPointSize(10)
				configs.setValue('HexView2.hex.Font', self.fontHex.toString())


		elif mod == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier:
			if e.key() == QtCore.Qt.Key_C:
				self.copySelection("hexdump")
			elif e.key() == QtCore.Qt.Key_I:
				self.fiTreeWidget.fileOpenFormatInfo()


		elif mod == QtCore.Qt.NoModifier:
			if e.key() == QtCore.Qt.Key_X:
				self.deleteSelectedStyle()

			if QtCore.Qt.Key_A <= e.key() <= QtCore.Qt.Key_Z:
				letter = chr(e.key() - QtCore.Qt.Key_A + 0x41)
				info = next((x for x in HexView2.userStyles if x[0] == letter), None)
				if info:
					self.styleSelection(**info[2])



	#################  data setters   ##########################################
	def getBytes(self):
		return self.buffers[0].buffer

	def setBytes(self, buf : bytes):
		abuf = ByteBuffer(buf)
		self.setBuffer(abuf)
	
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
			self.fiTreeWidget.formatInfoContainer = self.buffers[0].fi_container
		self.fiTreeWidget.updateTree(self.buffers[0].fi_tree)
		if self.buffers[0].fi_tree is None: self.applyFormatInfo()

	############ RENDERING ############################################################

	def resizeEvent(self, e):
		self.redraw();
		self.fiTreeWidget.resize(self.width() - self.fiTreeWidget.pos().x()-10, self.height()-40)
		self.annotationSelect.move(10, self.height() - 28)
		self.fiSelect.move(self.xAscii + self.dxAscii*self.bytesPerLine + 10, self.height() - 28)
		self.annotationSelect.setFixedWidth(self.xAscii + self.dxAscii*self.bytesPerLine-10)
		self.fiSelect.setFixedWidth(self.width() - self.fiTreeWidget.pos().x()-10)

	def sizeHint(self):
		return QSize(self.xAscii + self.dxAscii * self.bytesPerLine + 10, 256)

	def redraw(self):
		self.pixmapsInvalid = True
		for buffer in self.buffers:
			buffer.invalidateCaches()
		self.update()

	def drawPixmaps(self):
		if self.size().height() < 3 or self.size().width() < 3: return
		with PerfTimer("drawPixmaps"):
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

	def redrawSelection(self):
		self.update()

	def paintEvent(self, e):
		with PerfTimer("paintEvent"):
			if self.pixmapsInvalid:
				try:
					self.drawPixmaps()
				except:
					logging.exception("Failed to draw bg/text pixmaps")
				self.pixmapsInvalid = False
			try:
				qp = QPainter()
				qp.begin(self)
				qp.drawPixmap(0, 0, self.backgroundPixmap)
				self.drawSelection(qp)
				self.drawHover(qp)
				qp.drawPixmap(0, 0, self.textPixmap)
				#self.drawQuicktip(qp)
				qp.end()
			except:
				logging.exception("Failed to render HexView")

	def drawLines(self, qpTxt, qpBg):
		y = 0 - self.partialLineScrollY
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
		TXT_DY = self.fontAscent + self.linePadding #floor(self.dyLine*0.8)
		#qpTxt.set
		offset = self.lineNumberToByteOffset(lineNumber)
		end = min(len(buffer), offset + self.bytesPerLine)
		ii = 0
		for i in range(offset, end):
			theByte = buffer.getByte(i)

			#// if specified, print section header
			#sectionAnnotations = buffer.getAnnotationValues(start=i, annotationProperty="section");
			sectionAnnotations = buffer.ranges.getMetaValuesStartingAt(i, "section")
			if len(sectionAnnotations) != 0:
				if (ii != 0): y += self.dyLine;
				qpTxt.setPen(self.fsSection)
				for row in sectionAnnotations:
					bangs = len(pattern_heading.match(row).group())
					qpTxt.setFont(self.fontSection[bangs])
					qpTxt.drawText(self.xHex, y+self.fontSection[bangs].pointSize() * 1.7, row)
					y += self.fontSection[bangs].pointSize() * 2
				qpTxt.setFont(self.fontAddress)
				qpTxt.setPen(QColor("#555555"))
				if (ii != 0): qpTxt.drawText(self.xAddress, y+TXT_DY, self.addressFormat.format(i));

			if (ii == 0):  #//print address for first byte in line
				qpTxt.setFont(self.fontAddress)
				qpTxt.setPen(self.fsAddress)
				qpTxt.drawText(self.xAddress, y+TXT_DY, self.addressFormat.format(offset))

			#// if specified, draw background color from style attribute
			bg = buffer.getStyle(i, "color", None)
			fg = buffer.getStyle(i, "textcolor", None)
			if (bg):
				qpBg.fillRect(self.xHex + ii * self.dxHex + int(ii/self.hexSpaceAfter)*self.hexSpaceWidth + 2, y+1, self.dxHex, self.dyLine-2, QColor(bg))
				qpBg.fillRect(self.xAscii + ii * self.dxAscii, y+1, self.dxAscii, self.dyLine-2, QColor(bg))

			#// store item's Y position
			self.itemY.append(y)

			#// print HEX and ASCII representation of this byte
			qpTxt.setFont(self.fontHex)
			qpTxt.setPen( self.fsHex if not fg else QColor(fg))
			qpTxt.drawText(self.xHex + ii * self.dxHex + int(ii/self.hexSpaceAfter)*self.hexSpaceWidth + 2, y+TXT_DY, self.hexFormat.format(theByte));
			qpTxt.setFont(self.fontAscii)
			qpTxt.setPen(self.fsAscii if not fg else QColor(fg))
			asciichar = chr(theByte) if (theByte > 0x20 and theByte < 0x80) else "."
			qpTxt.drawText(self.xAscii + ii * self.dxAscii, y+TXT_DY, asciichar);
			ii += 1
		return y + self.dyLine

	def drawSelection(self, qp):
		selMin = max(self.firstLine*self.bytesPerLine, min(self.selStart, self.selEnd))
		selMax = max(self.selStart, self.selEnd)
		for i in range(selMin, selMax+1):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(i)
			if dy is None: break
			qp.fillRect(xHex, y, self.dxHex, dy, self.fsSel)
			qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsSel)

		for helper, meta in SelectionHelpers.types:
			if configs.getValue("SelHeur." + helper.__name__ + ".enabled", meta.get("defaultEnabled", False)):
				with PerfTimer("execution of selectionHelper (%s)", helper.__name__):
					helper(self, qp, self.buffers[0], (selMin, selMax))

	def drawHover(self, qp):
		if self.lastHit is not None:
			(xHex, xAscii, y, dy) = self.offsetToClientPos(self.lastHit)
			if dy is not None:
				qp.fillRect(xHex, y, self.dxHex, dy, self.fsHover)
				qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsHover)

	########### CALCULATION    #########################
	def lineNumberToByteOffset(self, lineNumber:int):
		return lineNumber * self.bytesPerLine

	def maxLine(self):
		return ceil(len(self.buffers[0]) / self.bytesPerLine);

	def maxVisibleLine(self):
		return self.firstLine + ceil(len(self.itemY)/self.bytesPerLine)

	def offsetToClientPos(self, offset):
		pos = offset % self.bytesPerLine
		visibleIdx = offset - self.bytesPerLine*self.firstLine
		if visibleIdx < 0 or visibleIdx >= len(self.itemY):
			logging.warn("trying to paint outside viewport %r", offset)
			return (None, None, None, None)
		y = self.itemY[visibleIdx]
		return (self.xHex + pos * self.dxHex + int(pos/self.hexSpaceAfter)*self.hexSpaceWidth, self.xAscii + self.dxAscii*pos,y+floor(self.linePadding*0.5),ceil(self.charHeight*1.2))

	def visibleRange(self):
		firstVisibleOffset = self.bytesPerLine*self.firstLine
		return (firstVisibleOffset, firstVisibleOffset + len(self.itemY))


def showHexView2Dialog(parent, title, content, ok_callback):
	hexview = HexView2()
	hexview.setBytes(content)
	return showWidgetDlg(hexview, title, lambda: hexview.getBytes(), ok_callback)


if __name__ == '__main__':
	app = QApplication(sys.argv)
	ex = HexView2()
	ex.show()
	ex.setBytes(open(sys.argv[1], "rb").read())
	sys.exit(app.exec_())

