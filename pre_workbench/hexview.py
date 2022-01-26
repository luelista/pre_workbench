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


import sys
import traceback
from math import ceil, floor

from PyQt5 import QtCore
from PyQt5.QtCore import (Qt, QSize, pyqtSignal, QObject)
from PyQt5.QtGui import QPainter, QFont, QColor, QPixmap, QFontMetrics, QKeyEvent, QStatusTipEvent
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSizePolicy, QMessageBox, QAction, QDialog, QVBoxLayout

from pre_workbench import configs
from pre_workbench import structinfo
from pre_workbench.configs import SettingsSection
from pre_workbench.guihelper import setClipboardText, str_ellipsis, GlobalEvents, showWidgetDlg
from pre_workbench.hexview_selheur import selectionHelpers
from pre_workbench.objects import ByteBuffer, parseHexFromClipboard, BidiByteBuffer
from pre_workbench.algo.rangelist import Range
from pre_workbench.rangetree import RangeTreeWidget
from pre_workbench.structinfo.exceptions import parse_exception
from pre_workbench.structinfo.parsecontext import BytebufferAnnotatingParseContext


class Helper(QObject):
	onOptionUpdated = pyqtSignal(str, object)
HV2Helper = Helper()

group = SettingsSection('HexView2', 'Hex Editor', 'address', 'Address Styles')
configs.registerOption(group, 'FontFamily', 'Address FontFamily', 'text', {}, 'monospace', HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'FontSize', 'Address FontSize', 'int', {'min': 1, 'max': 1024}, 10, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'Color', 'Address Color', 'color', {}, '#888888',HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'Format', 'Address Format', 'text', {}, '{:08x}',HV2Helper.onOptionUpdated.emit)

group = SettingsSection('HexView2', 'Hex Editor', 'hex', 'Hex Styles')
configs.registerOption(group, 'FontFamily', 'Hex FontFamily', 'text', {}, 'monospace',HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'FontSize', 'Hex FontSize', 'int', {'min': 1, 'max': 1024}, 10, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'Color', 'Hex Color', 'color', {}, '#ffffff', HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'SpaceAfter', 'Hex SpaceAfter', 'int', {'min': 1, 'max': 1024}, 8, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'SpaceWidth', 'Hex SpaceWidth', 'int', {'min': 1, 'max': 1024}, 8, HV2Helper.onOptionUpdated.emit)

group = SettingsSection('HexView2', 'Hex Editor', 'ascii', 'ASCII Styles')
configs.registerOption(group, 'FontFamily', 'ASCII FontFamily', 'text', {}, 'monospace',HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'FontSize', 'ASCII FontSize', 'int', {'min': 1, 'max': 1024}, 10, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'Color', 'ASCII Color', 'color', {}, '#bbffbb', HV2Helper.onOptionUpdated.emit)

group = SettingsSection('HexView2', 'Hex Editor', 'section', 'Section Styles')
configs.registerOption(group, 'FontFamily', 'Section FontFamily', 'text', {}, 'serif',HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'FontSize', 'Section FontSize', 'int', {'min': 1, 'max': 1024}, 8, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'Color', 'Section Color', 'color', {}, '#aaaaaa', HV2Helper.onOptionUpdated.emit)

group = SettingsSection('HexView2', 'Hex Editor', 'general', 'General')
configs.registerOption(group, 'lineHeight', 'lineHeight', 'double', {'min': 0.1, 'max': 10}, 1.1, HV2Helper.onOptionUpdated.emit)
configs.registerOption(group, 'bytesPerLine', 'bytesPerLine', 'int', {'min': 1, 'max': 1024}, 16, HV2Helper.onOptionUpdated.emit)

class HexView2(QWidget):
	onNewSubflowCategory = pyqtSignal(str, object)
	formatInfoUpdated = pyqtSignal()
	selectionChanged = pyqtSignal(object)

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
		HV2Helper.onOptionUpdated.connect(self.loadOptions)
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



	def loadOptions(self, *dummy):

		self.bytesPerLine = configs.getValue('HexView2.general.bytesPerLine')
		self.addressFormat = configs.getValue('HexView2.address.Format')

		self.xAddress = 5
		self.fontAddress = QFont(configs.getValue('HexView2.address.FontFamily'), configs.getValue('HexView2.address.FontSize'), QFont.Light)
		self.fsAddress = QColor(configs.getValue('HexView2.address.Color'))

		self.xHex = QFontMetrics(self.fontAddress).width(self.addressFormat.format(0)) + 15
		self.fontHex = QFont(configs.getValue('HexView2.hex.FontFamily'), configs.getValue('HexView2.hex.FontSize'), QFont.Light)
		self.fsHex = QColor(configs.getValue('HexView2.hex.Color'));	self.dxHex = QFontMetrics(self.fontHex).width("00")+4
		self.hexSpaceAfter = configs.getValue('HexView2.hex.SpaceAfter'); self.hexSpaceWidth = configs.getValue('HexView2.hex.SpaceWidth')

		self.xAscii = self.xHex + self.dxHex*self.bytesPerLine+(ceil(self.bytesPerLine/self.hexSpaceAfter)-1)*self.hexSpaceWidth+15
		self.fontAscii = QFont(configs.getValue('HexView2.ascii.FontFamily'), configs.getValue('HexView2.ascii.FontSize'), QFont.Light)
		self.fsAscii = QColor(configs.getValue('HexView2.ascii.Color')); self.dxAscii = QFontMetrics(self.fontAscii).width("W")

		self.fsSel = QColor("#7fff9bff");  self.fsHover = QColor("#7f9b9bff")
		self.fontSection = QFont(configs.getValue('HexView2.section.FontFamily'), configs.getValue('HexView2.section.FontSize'), QFont.Light)
		self.fsSection = QColor(configs.getValue('HexView2.section.Color'));

		self.dyLine = max(QFontMetrics(self.fontAddress).height(), QFontMetrics(self.fontHex).height()) * configs.getValue('HexView2.general.lineHeight')

		self.fiTreeWidget.move(self.xAscii + self.dxAscii*self.bytesPerLine + 10, 10)
		self.redraw()


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


	def buildGeneralContextMenu(self, ctx):
		ctx.addAction("Select all", lambda: self.selectAll())

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
		selection = self.selRange()
		try:
			match = next(self.buffers[0].matchRanges(start=selection.start, end=selection.end))
		except StopIteration:
			match = selection
			self.buffers[0].addRange(selection)

		match.metadata.update(kw)



	################# FI Tree ####################################################

	def applyFormatInfo(self):
		if self.fiTreeWidget.formatInfoContainer != None:
			# TODO clear out the old ranges from the last run, but don't delete ranges from other sources (e.g. style, bidi-buf)
			try:
				self.formatInfoUpdated.emit()
				parse_context = BytebufferAnnotatingParseContext(self.fiTreeWidget.formatInfoContainer, self.buffers[0])
				parse_context.on_new_subflow_category = self.newSubflowCategory
				self.buffers[0].fi_tree = parse_context.parse()
				self.fiTreeWidget.updateTree(self.buffers[0].fi_tree)
				self.redraw()
			except parse_exception as ex:
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
		r = self.selRange()
		self.fiTreeWidget.hilightFormatInfoTree(r)
		#GlobalEvents.on_select_bytes.emit(self.buffers[bufferIdx], r)
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
				self.fiTreeWidget.loadFormatInfo(load_from_file=configs.getValue(self.fiTreeWidget.optionsConfigKey+"_lastOpenFile",""))
			elif e.key() == QtCore.Qt.Key_F5:
				self.applyFormatInfo()
			elif e.key() == QtCore.Qt.Key_Plus:
				configs.setValue('HexView2.addressFontSize', configs.getValue("HexView2.addressFontSize") + 1)
				configs.setValue('HexView2.hexFontSize', configs.getValue("HexView2.hexFontSize") + 1)
				configs.setValue('HexView2.asciiFontSize', configs.getValue("HexView2.asciiFontSize") + 1)
				configs.setValue('HexView2.sectionFontSize', configs.getValue("HexView2.sectionFontSize") + 1)

			elif e.key() == QtCore.Qt.Key_Minus:
				configs.setValue('HexView2.addressFontSize', configs.getValue("HexView2.addressFontSize") - 1)
				configs.setValue('HexView2.hexFontSize', configs.getValue("HexView2.hexFontSize") - 1)
				configs.setValue('HexView2.asciiFontSize', configs.getValue("HexView2.asciiFontSize") - 1)
				configs.setValue('HexView2.sectionFontSize', configs.getValue("HexView2.sectionFontSize") - 1)

			elif e.key() == QtCore.Qt.Key_0:
				configs.setValue('HexView2.addressFontSize', 10)
				configs.setValue('HexView2.hexFontSize', 10)
				configs.setValue('HexView2.asciiFontSize', 10)
				configs.setValue('HexView2.sectionFontSize', 8)


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
			self.fiTreeWidget.formatInfoContainer = self.buffers[0].fi_container
		self.fiTreeWidget.updateTree(self.buffers[0].fi_tree)
		if self.buffers[0].fi_tree == None: self.applyFormatInfo()

	def getBytes(self):
		return self.buffers[0].buffer

	############ RENDERING ############################################################

	def resizeEvent(self, e):
		self.redraw();
		self.fiTreeWidget.resize(self.width() - self.fiTreeWidget.pos().x()-10, self.height()-20)

	def sizeHint(self):
		return QSize(self.xAscii + self.dxAscii * self.bytesPerLine + 10, 256)

	def redraw(self):
		self.pixmapsInvalid = True
		self.update()

	def drawPixmaps(self):
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
		self.pixmapsInvalid = False

	def redrawSelection(self):
		self.update()

	def paintEvent(self, e):
		if self.pixmapsInvalid:
			self.drawPixmaps()
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
			#sectionAnnotations = buffer.getAnnotationValues(start=i, annotationProperty="section");
			sectionAnnotations = buffer.ranges.getMetaValuesStartingAt(i, "section")
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
		selMin = max(self.firstLine*self.bytesPerLine, min(self.selStart, self.selEnd))
		selMax = max(self.selStart, self.selEnd)
		for i in range(selMin, selMax+1):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(i)
			if xHex == 0 and dy == 0: break
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

