#!/usr/bin/python3
# -*- coding: utf-8 -*-



import sys
from PyQt5.QtWidgets import QWidget, QApplication, QMenu, QSizePolicy
from PyQt5.QtGui import QIcon, QPainter, QFont, QColor, QPixmap
from PyQt5.QtCore import (Qt, pyqtSignal, QObject, QSize)

from guihelper import setClipboardText
from objects import ByteBuffer, Range
from hexdump import hexdump
from math import ceil, floor

class HexView2(QWidget):
	def __init__(self, byteBuffer=None):
		super().__init__()
		self.firstLine = 0
		self.scrollY = 0
		
		self.backgroundPixmap = QPixmap()
		self.textPixmap = QPixmap()

		self.fontAddress = QFont('monospace', 10, QFont.Light)
		self.xAddress = 5; self.fsAddress = QColor("#888888")
		self.fontHex = QFont('monospace', 10, QFont.Light)
		self.xHex = 80; 		self.fsHex = QColor("#ffffff");	 self.dxHex = 20;
		self.fontAscii = QFont('monospace', 10, QFont.Light)
		self.xAscii = 410; 	self.fsAscii = QColor("#bbffbb"); self.dxAscii = 8;
		self.fsSel = QColor("#7fff9bff");  self.fsHover = QColor("#7f9b9bff");
		self.fontSection = QFont('Serif', 8, QFont.Light)
		self.fsSection = QColor("#aaaaaa");
		self.dyLine = 18;
		self.bytesPerLine = 16;

		self.selStart = 0;
		self.selEnd = 0;
		self.itemY = list()
		self.lastHit = None
		self.selecting = False
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.onCustomContextMenuRequested)
		if byteBuffer == None:
			self.showHex(bytes())
		else:
			self.setBuffer(byteBuffer)
		self.setMouseTracking(True)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
	
	def onCustomContextMenuRequested(self, point):
		hit = self.hitTest(point)
		ctxMenu = None
		if hit != None:
			if hit < self.selStart or hit > self.selEnd:
				self.selStart = self.selEnd = hit
				self.selecting = False
				self.redrawSelection()
			ctxMenu = self.buildSelectionContextMenu()
		else:
			ctxMenu = self.buildGeneralContextMenu()
		ctxMenu.exec(self.mapToGlobal(point))

	def buildSelectionContextMenu(self):
		ctx = QMenu("Context menu", self)
		ctx.addAction("Copy selection hex", lambda: setClipboardText(self.buffers[0].toHex(self.selFirst(), self.selLength(), " ", "%02X")))
		ctx.addAction("Copy selection C Array", lambda: setClipboardText(self.buffers[0].toHex(self.selFirst(), self.selLength(), ", ", "0x%02X")))
		ctx.addSeparator()
		ctx.addAction("Selection %d-%d"%(self.selStart,self.selEnd))
		ctx.addSeparator()
		for d in self.buffers[0].matchRanges(overlaps=self.selRange()):
			ctx.addAction("Range %d-%d (%s): %s" % (d.start, d.end, d.metadata.get("name"), d.metadata.get("showname")), lambda d=d: self.selectRange(d))
			for k,v in d.metadata.items():
				if k != "name" and k != "showname":
					ctx.addAction("    %s=%s" % (k,v))
		return ctx
	def buildGeneralContextMenu(self):
		ctx = QMenu("Context menu", self)
		ctx.addAction("Select all", lambda: self.select(0, len(self.buffers[0])))
		return ctx


	def wheelEvent(self, e):
		if e.pixelDelta().isNull():
			deltaY = e.angleDelta().y() / 4
		else:
			deltaY = e.pixelDelta().y()
		self.scrollY = max(0, min((self.maxLine()-1)*self.dyLine, self.scrollY - deltaY))
		self.firstLine = ceil(self.scrollY / self.dyLine)
		print("wheel",deltaY,self.scrollY)
		self.redraw()

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
		self.redrawSelection()
		print("selection changed",self.selStart, self.selEnd, self.lastHit)

	def selFirst(self):
		return min(self.selStart, self.selEnd)
	def selLength(self):
		return max(self.selStart, self.selEnd) - self.selFirst() + 1
	def selRange(self):
		return Range(min(self.selStart,self.selEnd), max(self.selStart,self.selEnd))

	def select(self, start:int, end:int):
		self.selStart = start; self.selEnd = end; self.redrawSelection();
		print("selection changed",self.selStart, self.selEnd, self.lastHit);
	def selectRange(self, rangeObj):
		self.select(rangeObj.start, rangeObj.end)
	
	def showHex(self, buf : bytes):
		#abuf = ByteBuffer();
		#abuf.setBytes(0, buf, undefined, undefined);
		abuf = ByteBuffer(buf)
		self.buffers = [ abuf ];
		self.firstLine = 0;
		self.redraw();
	
	def setBuffer(self, bbuf):
		self.buffers = [ bbuf ];
		self.firstLine = 0;
		self.redraw();
	
	def showPacketHex(self, packet):
		print("showPacketHex",packet)
		self.buffers = [ preparePacketHex(packet) ];
		print("prepared:",self.buffers)
		self.firstLine = 0;
		self.redraw();
	
	def lineNumberToByteOffset(self, lineNumber:int):
		return lineNumber * self.bytesPerLine;
	
	def maxLine(self):
		return ceil(len(self.buffers[0]) / self.bytesPerLine);
	
	def resizeEvent(self, e):
		self.redraw();
	
	def hitTest(self, point):
		x, y = point.x(), point.y()
		linePos = None
		if (x >= self.xAscii):
			pos = floor((x - self.xAscii) / self.dxAscii);
			if (pos < self.bytesPerLine): linePos = pos; #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}
		elif (x >= self.xHex):
			pos = floor((x - self.xHex) / self.dxHex);
			if (pos < self.bytesPerLine): linePos = pos; #//return {'hit':'ascii', 'line':i+self.firstLine, 'pos':pos, ''}
		
		#//console.log(x,y,linePos);
		if (linePos is None): return None

		for i in range(linePos, len(self.itemY), self.bytesPerLine):
			#//console.log(i,self.itemY[i],y,self.itemY[i] <= y , y <= self.itemY[i]+self.dyLine)
			if (self.itemY[i] <= y and y <= self.itemY[i]+self.dyLine):
				return self.lineNumberToByteOffset(self.firstLine) + i;
		
		return None

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
				qpTxt.drawText(5, y+TXT_DY, "\n".join(sectionAnnotations))
				y += self.dyLine;
				qpTxt.setFont(self.fontHex)
				qpTxt.setPen(QColor("#555555"));
				if (ii != 0): qpTxt.drawText(self.xAddress, y+TXT_DY, "%08x"%(i));
			
			
			if (ii == 0):  #//print address for first byte in line
				qpTxt.setFont(self.fontAddress)
				qpTxt.setPen(self.fsAddress);
				qpTxt.drawText(self.xAddress, y+TXT_DY, "%08x"%(offset));
			

			#// if specified, draw background color from style attribute
			bg = buffer.getStyle(i, "color", None);
			if (bg):
				qpBg.fillRect(self.xHex + (ii) * self.dxHex, y, self.dxHex, self.dyLine-2, QColor(bg));
			

			#// store item's Y position
			self.itemY.append(y)

			#// print HEX and ASCII representation of this byte
			qpTxt.setFont(self.fontHex)
			qpTxt.setPen(self.fsHex)
			qpTxt.drawText(self.xHex + ii * self.dxHex+2, y+TXT_DY, "%02x"%(theByte));
			qpTxt.setFont(self.fontAscii)
			qpTxt.setPen(self.fsAscii)
			asciichar = chr(theByte) if (theByte > 0x20 and theByte < 0x80) else "."
			qpTxt.drawText(self.xAscii + ii * self.dxAscii, y+TXT_DY, asciichar);
			ii += 1
		return y + self.dyLine

	def offsetToClientPos(self, offset):
		pos = offset % self.bytesPerLine;
		visibleIdx = offset - self.bytesPerLine*self.firstLine
		if visibleIdx < 0 or visibleIdx >= len(self.itemY): return (0,0,0,0)
		y = self.itemY[visibleIdx]
		return (self.xHex + self.dxHex*pos, self.xAscii + self.dxAscii*pos,y,self.dyLine)
	
	def drawSelection(self, qp):
		selMin = min(self.selStart, self.selEnd)
		selMax = max(self.selStart, self.selEnd)
		for i in range(selMin, selMax+1):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(i)
			qp.fillRect(xHex, y, self.dxHex, dy, self.fsSel)
			qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsSel)

	def drawHover(self, qp):
		if (self.lastHit != None):
			(xHex, xAscii, y, dy) = self.offsetToClientPos(self.lastHit)
			qp.fillRect(xHex, y, self.dxHex, dy, self.fsHover)
			qp.fillRect(xAscii, y, self.dxAscii, dy, self.fsHover)
		




if __name__ == '__main__':
	app = QApplication(sys.argv)
	ex = HexView2()
	ex.show()
	ex.showHex(open(sys.argv[1], "rb").read())
	sys.exit(app.exec_())

