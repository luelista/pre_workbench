import struct

from PyQt5.QtGui import QColor


def extendRange(bbuf, range, amount=16):
	(selMin, selMax) = range
	return max(0, selMin - amount), min(bbuf.length, selMax + amount)

def rangeBefore(bbuf, range, amount=16):
	(selMin, selMax) = range
	return max(0, selMin - amount), selMin

def intToVarious(*values):
	for value in values:
		if value < 0:
			yield from intToFmts(value, [">q","<q",">i","<i",">h","<h",">b","<b"])
		else:
			yield from intToFmts(value, [">Q","<Q",">I","<I",">H","<H",">B","<B"])
		yield str(value).encode("utf-8"), "d"
		yield ("%x"%value).encode("utf-8"), "x"
		yield ("%X"%value).encode("utf-8"), "X"


def intToFmts(value, fmts):
	for fmt in fmts:
		try:
			yield struct.pack(fmt, value), fmt
		except:
			pass

def findInRange(bbuf, ranges, values):
	for (start, end) in ranges:
		for val, desc in values:
			l = len(val)
			for i in range(start, end-l+1):
				if bbuf.buffer[i:i+l] == val:
					return (i, i+l), desc
	return None, None

def highlightMatch(editor, qp, matchrange, desc, color):
	(start,end)=matchrange
	for i in range(start,end):
		(xHex, xAscii, y, dy) = editor.offsetToClientPos(i)
		qp.fillRect(xHex, y, editor.dxHex, dy, color)
		qp.fillRect(xAscii, y, editor.dxAscii, dy, color)


def selectionLengthMatcher(editor, qp, bbuf, sel):
	(start, end) = sel
	sellen = end - start
	print (start,end,sellen,[rangeBefore(bbuf, sel), sel])
	if sellen == -1: return
	match, desc = findInRange(bbuf, [rangeBefore(bbuf, sel), sel], intToVarious(sellen+1, sellen+2, sellen+4, sellen-1))
	if match != None:
		highlightMatch(editor, qp, match,desc,QColor("#ff00ff"))



selectionHelpers = [ selectionLengthMatcher ]
