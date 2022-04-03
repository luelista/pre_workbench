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
from base64 import b64decode
from collections import namedtuple
from math import ceil, floor

from PyQt5.QtCore import (Qt, QSize, pyqtSignal)
from PyQt5.QtGui import QPainter, QFont, QColor, QPixmap, QFontMetrics, QKeyEvent, QStatusTipEvent, QMouseEvent
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSizePolicy, QAction, QInputDialog

from pre_workbench import configs
from pre_workbench.algo.range import Range
from pre_workbench.configs import SettingsSection
from pre_workbench.guihelper import setClipboardText, GlobalEvents, showWidgetDlg, getClipboardText
from pre_workbench.hexview_selheur import SelectionHelpers
from pre_workbench.objects import ByteBuffer, parseHexFromClipboard, BidiByteBuffer
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

HitTestResult = namedtuple('HitTestResult', ['buffer', 'offset', 'region'])

class HexView2(QWidget):
	onNewSubflowCategory = pyqtSignal(str, object)
	parseResultsUpdated = pyqtSignal(list)
	selectionChanged = pyqtSignal(object)

	userStyles = [
		("R", "Red", {"color": "#aa0000"}),
		("G", "Green", {"color": "#00aa00"}),
		("Y", "Yellow", {"color": "#aaaa00"}),
		("L", "Blue", {"color": "#0000aa"}),
		("M", "Magenta", {"color": "#aa00aa"}),
		("T", "Turqoise", {"color": "#00aaaa"}),
	]

	def __init__(self, byteBuffer=None, annotationSetDefaultName="", options=dict(), optionsConfigKey="HexViewParams", project=None, formatInfoContainer=None):
		super().__init__()
		self.project = project
		self.formatInfoContainer = formatInfoContainer
		if self.formatInfoContainer: self.formatInfoContainer.updated.connect(self._formatInfoUpdated)
		self.annotationSetDefaultName = annotationSetDefaultName
		self.annotationSetName = None
		self.buffers = list()
		self.firstLine = 0
		self.scrollY = 0
		self.partialLineScrollY = 0
		self.setFocusPolicy(Qt.StrongFocus)

		self.initUI()

		self.backgroundPixmap = QPixmap()
		self.textPixmap = QPixmap()
		GlobalEvents.on_config_change.connect(self._loadOptions)
		self._loadOptions()

		self.pixmapsInvalid = True
		self.selBuffer = 0
		self.selStart = 0
		self.selEnd = 0
		self.itemY = list()
		self.lastHit = None
		self.selecting = False
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self._onCustomContextMenuRequested)
		if byteBuffer is None:
			self.setBytes(bytes())
		else:
			self.setBuffer(byteBuffer)
		self.setMouseTracking(True)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

	def initUI(self):
		pass
		#self.fiTreeWidget = RangeTreeWidget(self)
		#self.fiTreeWidget.show()
		#self.fiTreeWidget.currentItemChanged.connect(self._fiTreeItemSelected)
		#self.fiTreeWidget.formatInfoUpdated.connect(self.applyFormatInfo)


	def _loadOptions(self, *dummy):
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

		self.fsSel = QColor("#7fddaaff");  self.fsCursor = QColor("#bfddaaff");  self.fsHover = QColor("#8fff9bff")
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

		#self.fiTreeWidget.move(self.xAscii + self.dxAscii*self.bytesPerLine + 10, 10)
		self.redraw()


	############ HEX VIEW CONTEXT MENU  #############################################################

	def _onCustomContextMenuRequested(self, point):
		hit = self._hitTest(point)
		ctxMenu = QMenu("Context menu", self)
		if hit is not None:
			if hit.offset < self.selStart or hit.offset > self.selEnd or hit.buffer != self.selBuffer:
				self.selStart = self.selEnd = hit.offset
				self.selBuffer = hit.buffer
				self.selecting = False
				self.redrawSelection()
			self._buildSelectionContextMenu(ctxMenu)
		else:
			self._buildGeneralContextMenu(ctxMenu)
		ctxMenu.exec(self.mapToGlobal(point))

	def _buildSelectionContextMenu(self, ctx):
		ctx.addAction(QAction("Copy selection hex\tCtrl-C", ctx, triggered=lambda: self.copySelection(), shortcut="Ctrl+C"))
		ctx.addAction("Copy selection C Array", lambda: self.copySelection((", ", "0x%02X")))
		ctx.addAction("Copy selection hexdump\tCtrl-Shift-C", lambda: self.copySelection("hexdump"))
		#ctx.addAction("Copy selected annotations", lambda: self.copySelection("hexdump"))
		ctx.addSeparator()
		#ctx.addAction("Selection %d-%d (%d bytes)"%(self.selStart,self.selEnd,self.selLength()))
		#ctx.addAction("Selection 0x%X - 0x%X (0x%X bytes)"%(self.selStart,self.selEnd,self.selLength()))
		try:
			match = next(
				self.buffers[self.selBuffer].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))

			ctx.addAction("&Delete selected style\tX", lambda: self.deleteSelectedStyle())

			ctx.addSeparator()
		except StopIteration:
			pass
		for key, name, style in HexView2.userStyles:
			ctx.addAction(name+"\t"+key, lambda: self.styleSelection(**style))
		ctx.addSeparator()
		ctx.addAction("&Start Section...", lambda: self.setSectionSelection())
		ctx.addSeparator()

		if self.selLength() > 1:
			if self.project:
				menu = ctx.addMenu( "Apply annotation set for selection")
				for name in self.project.getAnnotationSetNames():
					#TODO implement this
					menu.addAction(name, lambda name=name: print(name))
		else:
			if self.project:
				menu = ctx.addMenu("Load annotation set")
				for name in self.project.getAnnotationSetNames():
					menu.addAction(name, lambda name=name: self.loadAnnotations(name, self.selBuffer))

			if self.formatInfoContainer:
				menu = ctx.addMenu("Apply format info")
				for name in self.formatInfoContainer.definitions.keys():
					menu.addAction(name, lambda name=name: self.applyFormatInfo(name, self.selBuffer))
				#menu.addAction("New...", lambda: )

	def _buildGeneralContextMenu(self, ctx):
		ctx.addAction("Select all", lambda: self.selectAll())
		ctx.addSeparator()
		ctx.addAction("Paste", lambda: self.setBuffer(parseHexFromClipboard()))
		menu = ctx.addMenu("Paste as")
		menu.addAction("Base64", lambda: self.setBuffer(ByteBuffer(b64decode(getClipboardText()))))
		ctx.addAction("Clear ranges", lambda: self.clearRanges())

		if self.project:
			menu = ctx.addMenu("Load annotation set" + (" on all buffers" if len(self.buffers) > 0 else ""))
			for name in self.project.getAnnotationSetNames():
				menu.addAction(name, lambda name=name: self.loadAnnotations(name))

		if self.formatInfoContainer:
			menu = ctx.addMenu("Apply format info" + (" on all buffers" if len(self.buffers) > 0 else ""))
			for name in self.formatInfoContainer.definitions.keys():
				menu.addAction(name, lambda name=name: self.applyFormatInfo(name))

	def setDefaultAnnotationSet(self, name):
		self.annotationSetDefaultName = name
		self.loadAnnotations(name)

	def loadAnnotations(self, set_name, bufIdx=None):
		for buf in self.buffers if bufIdx is None else [self.buffers[bufIdx]]:
			buf.setRanges(buf.matchRanges(hasMetaKey='_sdef_ref'))
			annotations = self.project.getAnnotations(set_name)
			for rowid, start, end, meta_str in annotations:
				meta = json.loads(meta_str)
				if meta.get("deleted"): continue
				meta['rowid'] = rowid
				buf.addRange(Range(start=start, end=end, meta=meta))
		self.redraw()
		self.annotationSetName = set_name

	def storeAnnotaton(self, range):
		if not self.annotationSetName or not self.project: return
		self.project.storeAnnotation(self.annotationSetName, range)

	def clearRanges(self):
		self.buffers[0].clearRanges()
		self.redraw()

	def getRangeString(self, range, style=(" ","%02X")):
		if isinstance(style, tuple):
			return self.buffers[range.buffer_idx].toHex(range.start, range.length(), style[0], style[1])
		elif style=="hexdump":
			return self.buffers[range.buffer_idx].toHexDump(range.start, range.length())

	def copySelection(self, style=(" ","%02X")):
		setClipboardText(self.getRangeString(self.selRange(), style))

	def styleSelection(self, **kw):
		selection = self.selRange()
		try:
			match = next(self.buffers[self.selBuffer].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))
		except StopIteration:
			match = selection
			self.buffers[self.selBuffer].addRange(selection)

		match.metadata.update(kw)
		self.storeAnnotaton(match)
		self.redraw()

	def setSectionSelection(self):
		selection = self.selRange()
		try:
			match = next(self.buffers[self.selBuffer].matchRanges(start=selection.start, doesntHaveMetaKey='_sdef_ref'))
			title = match.metadata.get("section")
		except StopIteration:
			match = None
			title = ""

		newTitle, ok = QInputDialog.getText(self, "Section", "Enter section title:", text=title)
		if ok:
			if match is None:
				match = selection
				self.buffers[self.selBuffer].addRange(selection)
			match.metadata.update(section=newTitle)
			self.storeAnnotaton(match)
			self.redraw()

	def deleteSelectedStyle(self):
		try:
			match = next(
				self.buffers[self.selBuffer].matchRanges(start=self.selFirst(), end=self.selLast()+1, doesntHaveMetaKey='_sdef_ref'))
			self.buffers[self.selBuffer].removeRange(match)
			match.metadata["deleted"] = True
			self.storeAnnotaton(match)
			self.redraw()
		except StopIteration:
			pass


	################# FI Tree ####################################################

	def _formatInfoUpdated(self):
		self.applyFormatInfo()

	def _parseBuffer(self, buf):
		if buf.fi_root_name is None: return
		try:
			# clear out the old ranges from the last run, but don't delete ranges from other sources (e.g. style, bidi-buf)
			buf.setRanges(buf.matchRanges(doesntHaveMetaKey='_sdef_ref'))
			parse_context = BytebufferAnnotatingParseContext(self.formatInfoContainer, buf)
			parse_context.on_new_subflow_category = self._newSubflowCategory
			buf.fi_tree = parse_context.parse(buf.fi_root_name)
		except parse_exception as ex:
			logging.exception("Failed to apply format info")
			logging.getLogger("DataSource").error("Failed to apply format info: " + str(ex))

	def applyFormatInfo(self, root_name=None, bufIdx=None):
		for buf in self.buffers if bufIdx is None else [self.buffers[bufIdx]]:
			if root_name is not None: buf.fi_root_name = root_name
			self._parseBuffer(buf)
		# QMessageBox.warning(self, "Failed to apply format info", str(ex))
		self.parseResultsUpdated.emit([buf.fi_tree for buf in self.buffers])
		self.redraw()

	def _newSubflowCategory(self, category, parse_context, **kv):
		logging.debug("on_new_subflow_category: %r",category)
		self.onNewSubflowCategory.emit(category, parse_context)

	def _fiTreeItemSelected(self, item, previous):
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
			self._setFirstLine(line - 2)
		elif line >= self.maxVisibleLine():
			self._setFirstLine(line - 5)  #TODO - ich weiß vorher nicht, wie viele zeilen auf den schirm passen

	def _setFirstLine(self, line):
		self.firstLine = max(0, min(self.maxLine()-1, line))
		self.scrollY = self.firstLine * self.dyLine
		self.redraw()

	############## MOUSE EVENTS - SELECTION  ############################

	def mouseMoveEvent(self, e):
		hit = self._hitTest(e.pos())
		if hit == self.lastHit: return
		self.lastHit = hit
		if self.selecting and hit is not None and hit.buffer == self.selBuffer: self.selEnd = hit.offset
		self.redrawSelection()

	def mousePressEvent(self, e):
		if e.button() != Qt.LeftButton: return
		hit = self._hitTest(e.pos())
		if hit is None: return
		self.lastHit = hit
		self.selStart = self.selEnd = hit.offset
		self.selBuffer = hit.buffer
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

		hit = self._hitTest(e.pos())
		if hit and hit.region == 'ascii':
			start, end = self._extendRangeMatch(hit.offset, hit.buffer, lambda c: 32 < c < 128)
			self.select(start, end, hit.buffer)

	def _extendRangeMatch(self, start, bufIdx, matcher):
		end = start
		buf = self.buffers[bufIdx]
		if not matcher(buf.buffer[start]): return (start, start)
		while start > 0:
			if not matcher(buf.buffer[start - 1]): break
			start -= 1
		while end < buf.length:
			if not matcher(buf.buffer[end + 1]): break
			end += 1
		return (start,end)

	def _hitTest(self, point):
		x, y = point.x(), point.y()
		linePos = None
		if (x >= self.xAscii):
			pos = floor((x - self.xAscii) / self.dxAscii);
			if (pos < self.bytesPerLine): linePos = pos; region = 'ascii' #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}
		elif (x >= self.xHex):
			xx = (x - self.xHex)
			xx -= floor(xx / (self.dxHex*self.hexSpaceAfter + self.hexSpaceWidth)) * self.hexSpaceWidth # correction factor for hex grouping
			pos = floor(xx / self.dxHex);
			if (pos < self.bytesPerLine): linePos = pos; region = 'hex' #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}

		#//console.log(x,y,linePos);
		if (linePos is None): return None

		for i in range(linePos, len(self.itemY), self.bytesPerLine):
			#//console.log(i,self.itemY[i],y,self.itemY[i] <= y , y <= self.itemY[i]+self.dyLine)
			bufIdx, bufOffset, itemY = self.itemY[i]
			if itemY is not None and itemY <= y and y <= itemY+self.dyLine:
				return HitTestResult(bufIdx, bufOffset, region)

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
		if bufferIdx >= len(self.buffers): return 0
		return max(0, min(len(self.buffers[bufferIdx]) - 1, pos))

	def select(self, start:int, end:int, bufferIdx=None, scrollIntoView=False):
		if bufferIdx is None: bufferIdx = self.selBuffer
		#TODO ensure that start, end are in valid range
		self.selStart = self.clipPosition(bufferIdx, start); self.selEnd = self.clipPosition(bufferIdx, end)
		self.selBuffer = bufferIdx
		if scrollIntoView:
			self.scrollIntoView(self.selEnd)
			self.scrollIntoView(self.selStart)

		self.redrawSelection()
		logging.debug("selection changed %r-%r (%r)",self.selStart, self.selEnd, self.lastHit)
		r = self.selRange()

		#self.fiTreeWidget.hilightFormatInfoTree(r)

		with PerfTimer("selectionChanged event handlers"):
			if self.selBuffer < len(self.buffers):
				self.selectionChanged.emit(r)

			QApplication.postEvent(self, QStatusTipEvent("Buffer #%d  Selection %d-%d (%d bytes)   0x%X - 0x%X (0x%X bytes)"%(
				self.selBuffer, self.selStart,self.selEnd,self.selLength(),self.selStart,self.selEnd,self.selLength())))


	def selectRange(self, rangeObj, scrollIntoView=False):
		self.select(rangeObj.start, max(rangeObj.start, rangeObj.end-1), bufferIdx=rangeObj.buffer_idx, scrollIntoView=scrollIntoView)

	def selectAll(self):
		self.select(0, len(self.buffers[self.selBuffer]), self.selBuffer)



	######## KEYBOARD EVENTS ###########################################

	def keyPressEvent(self, e: QKeyEvent) -> None:
		mod = e.modifiers() & ~Qt.KeypadModifier

		arrow = None
		if e.key() == Qt.Key_Left:
			arrow = self.selEnd - 1
		elif e.key() == Qt.Key_Right:
			arrow = self.selEnd + 1
		elif e.key() == Qt.Key_Up:
			arrow = self.selEnd - self.bytesPerLine
		elif e.key() == Qt.Key_Down:
			arrow = self.selEnd + self.bytesPerLine
		elif e.key() == Qt.Key_PageUp:
			arrow = self.selEnd - self.bytesPerLine * floor(self.height() / self.dyLine * 0.9)
		elif e.key() == Qt.Key_PageDown:
			arrow = self.selEnd + self.bytesPerLine * floor(self.height() / self.dyLine * 0.9)

		if arrow is not None:
			arrow = self.clipPosition(self.selBuffer, arrow)
			self.scrollIntoView(arrow)

		if arrow is not None and mod == Qt.ShiftModifier:
			self.select(self.selStart, arrow)

		elif arrow is not None and mod == Qt.NoModifier:
			self.select(arrow, arrow)

		elif mod == Qt.ControlModifier:
			if e.key() == Qt.Key_A:
				self.selectAll()
			elif e.key() == Qt.Key_C:
				self.copySelection()
			elif e.key() == Qt.Key_F5:
				self.applyFormatInfo()
			elif e.key() == Qt.Key_Plus:
				self.zoomIn()
			elif e.key() == Qt.Key_Minus:
				self.zoomOut()
			elif e.key() == Qt.Key_0:
				self.zoomReset()

		elif mod == Qt.ControlModifier | Qt.ShiftModifier:
			if e.key() == Qt.Key_C:
				self.copySelection("hexdump")

		elif mod == Qt.NoModifier:
			if e.key() == Qt.Key_X:
				self.deleteSelectedStyle()

			if Qt.Key_A <= e.key() <= Qt.Key_Z:
				letter = chr(e.key() - Qt.Key_A + 0x41)
				info = next((x for x in HexView2.userStyles if x[0] == letter), None)
				if info:
					self.styleSelection(**info[2])

		else:
			super().keyPressEvent(e)

	def focusInEvent(self, event) -> None:
		self.update()

	def focusOutEvent(self, event) -> None:
		self.update()

	def zoomIn(self):
		self.fontHex.setPointSize(self.fontHex.pointSize() + 1)
		configs.setValue('HexView2.hex.Font', self.fontHex.toString())
		GlobalEvents.on_config_change.emit()

	def zoomOut(self):
		self.fontHex.setPointSize(self.fontHex.pointSize() - 1)
		configs.setValue('HexView2.hex.Font', self.fontHex.toString())
		GlobalEvents.on_config_change.emit()

	def zoomReset(self):
		self.fontHex.setPointSize(10)
		configs.setValue('HexView2.hex.Font', self.fontHex.toString())
		GlobalEvents.on_config_change.emit()

	#################  data setters   ##########################################
	def getBytes(self):
		return self.buffers[0].buffer  # TODO handle multiple buffers!

	def setBytes(self, buf : bytes):
		abuf = ByteBuffer(buf)
		self.setBuffer(abuf)
	
	def setBuffer(self, bbuf):
		if isinstance(bbuf, BidiByteBuffer):
			self.buffers = bbuf.buffers
		elif isinstance(bbuf, ByteBuffer):
			self.buffers = [ bbuf ]
		elif isinstance(bbuf, list) and all(isinstance(item, ByteBuffer) for item in bbuf):
			self.buffers = bbuf
		else:
			raise TypeError("Invalid type passed to HexView2.setBuffer: "+str(type(bbuf)))
		self.firstLine = 0
		self.parseResultsUpdated.emit([buf.fi_tree for buf in self.buffers])
		self.select(0, 0, 0)
		self.redraw()

	############ RENDERING ############################################################

	def resizeEvent(self, e):
		self.redraw();
		#self.fiTreeWidget.resize(self.width() - self.fiTreeWidget.pos().x()-10, self.height()-40)

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
		self.itemY = list()
		if len(self.buffers) == 0: return
		maxLine = self.maxLine()
		lineNumber = self.firstLine
		while y < canvasHeight and lineNumber < maxLine:
			while len(self.itemY) % self.bytesPerLine != 0:
				self.itemY.append((None, None, None))

			y = self.drawLine(qpTxt, qpBg, lineNumber, y)
			lineNumber+=1
	
	def drawLine(self, qpTxt, qpBg, lineNumber, y):
		TXT_DY = self.fontAscent + self.linePadding #floor(self.dyLine*0.8)
		#qpTxt.set
		bufIdx, offset, _ = self.lineNumberToByteOffset(lineNumber)
		buffer = self.buffers[bufIdx]
		if offset == 0:
			# draw buffer separator
			qpBg.fillRect(2,y,100,1,QColor("red"))
			qpTxt.setFont(self.fontSection[0]); qpTxt.setPen(self.fsAscii)
			qpTxt.drawText(self.xHex, y+self.fontSection[0].pointSize() * 1.7, repr(buffer.metadata))
			y += self.fontSection[0].pointSize() * 2

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

			#// store item's Y position and buffer pos
			self.itemY.append((bufIdx, i, y))

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
		if len(self.buffers) == 0 or len(self.itemY) == 0: return

		selMin = min(self.selStart, self.selEnd)
		selMax = max(self.selStart, self.selEnd)
		selVisibleMin = max(self.itemY[0][1], selMin) if self.itemY[0][0] == self.selBuffer else selMin
		selVisibleMax = min(self.itemY[-1][1], selMax) if self.itemY[-1][0] == self.selBuffer else selMax
		for i in range(selVisibleMin, selVisibleMax+1):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(self.selBuffer, i)
			if dy is None: break
			fs = self.fsCursor if i == self.selEnd and self.hasFocus() else self.fsSel
			qp.fillRect(xHex, y, self.dxHex, dy, fs)
			qp.fillRect(xAscii, y, self.dxAscii, dy, fs)

		for helper, meta in SelectionHelpers.types:
			if configs.getValue("SelHeur." + helper.__name__ + ".enabled", meta.get("defaultEnabled", False)):
				with PerfTimer("execution of selectionHelper (%s)", helper.__name__):
					helper(self, qp, self.buffers[self.selBuffer], (self.selBuffer, selMin, selMax))

	def drawHover(self, qp):
		if self.lastHit is not None:
			(xHex, xAscii, y, dy) = self.offsetToClientPos(self.lastHit.buffer, self.lastHit.offset)
			if dy is not None:
				qp.fillRect(xHex, y, self.dxHex, dy, self.fsHover)
				qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsHover)

	########### CALCULATION    #########################
	def lineNumberToByteOffset(self, lineNumber:int):
		bufOffset = lineNumber * self.bytesPerLine
		bufIdx = 0
		while bufIdx < len(self.buffers) and bufOffset >= len(self.buffers[bufIdx]):
			bufOffset -= ceil(len(self.buffers[bufIdx]) / self.bytesPerLine) * self.bytesPerLine
			bufIdx += 1
		return HitTestResult(bufIdx, bufOffset, None)

	def maxLine(self):
		return sum(ceil(len(buffer) / self.bytesPerLine) for buffer in self.buffers);

	def maxVisibleLine(self):
		return self.firstLine + ceil(len(self.itemY)/self.bytesPerLine)

	def offsetToClientPos(self, buffer, offset):
		column = offset % self.bytesPerLine
		for bufIdx, bufOffset, itemY in self.itemY:
			if bufIdx == buffer and bufOffset == offset:
				return (self.xHex + column * self.dxHex + int(column / self.hexSpaceAfter) * self.hexSpaceWidth,
						self.xAscii + self.dxAscii * column,
						itemY + floor(self.linePadding * 0.5),
						ceil(self.charHeight * 1.2))
		logging.warning("trying to paint outside viewport %r", offset)
		return (None, None, None, None)

	def visibleRange(self):
		firstBuf, firstOffset, firstY = self.itemY[0]
		lastBuf, lastOffset, lastY = self.itemY[-1]
		return ((firstBuf, firstOffset), (lastBuf, lastOffset))


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

