
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
import logging
import struct
from typing import TYPE_CHECKING

from PyQt5.QtGui import QColor, QPen, QPainter

from pre_workbench.configs import SettingsField
from pre_workbench.objects import ByteBuffer
from pre_workbench.typeregistry import TypeRegistry

if TYPE_CHECKING:
	from pre_workbench.controls.hexview import HexView2

SelectionHelpers = TypeRegistry("SelectionHelpers")


def extendRange(bbuf, range, amount=16):
	(bufIdx, selMin, selMax) = range
	return bufIdx, max(0, selMin - amount), min(bbuf.length, selMax + amount)


def rangeBefore(bbuf, range, amount=16):
	(bufIdx, selMin, selMax) = range
	return bufIdx, max(0, selMin - amount), selMin



def intToVarious(*values):
	for value in values:
		if value < 0:
			yield from intToFmts(value, [">q","<q",">i","<i",">h","<h",">b","<b"])
		else:
			yield from intToFmts(value, [">Q","<Q",">I","<I",">H","<H",">B","<B"])
		yield str(value).encode("utf-8"), "d "+str(value)
		yield ("%x"%value).encode("utf-8"), "x "+str(value)
		yield ("%X"%value).encode("utf-8"), "X "+str(value)


def intToFmts(value, fmts):
	for fmt in fmts:
		try:
			yield struct.pack(fmt, value), "%s %d"%(fmt, value)
		except struct.error:
			pass


def findInRange(bbuf, ranges, values):
	for (bufIdx, start, end) in ranges:
		for val, desc in values:
			l = len(val)
			if l == 0: raise Exception("")
			i = start
			while i <= end-l:
				if bbuf.buffer[i:i+l] == val:
					yield (bufIdx, i, i+l), desc
					i += l
				else:
					i += 1



@SelectionHelpers.register(color="#ff00ff", defaultEnabled=True, options=[
	SettingsField("minLength", "Minimum Selection Length", "int", {"default":2}),
])
def selectionLengthMatcher(editor: "HexView2", qp: QPainter, bbuf: ByteBuffer, sel, options):
	"""
	Searches for the length of the selection in various formats in the 16 bytes preceding, the selection itself and the 16 bytes following the selection.

	Formats are int8 to int64, uint8 to uint64 (big and little endian), decimal string and hex string (lower and upper case).
	"""
	(bufIdx, start, end) = sel
	sellen = end - start + 1
	if sellen < options.get("minLength", 2): return
	for match, desc in findInRange(bbuf, [extendRange(bbuf, (bufIdx, start,start))], intToVarious(sellen)):
		editor.highlightMatch(qp, match, "Selection Length as " + desc, QColor("#ff00ff"))


@SelectionHelpers.register(color="#993399", defaultEnabled=False)
def fuzzySelectionLengthMatcher(editor: "HexView2", qp: QPainter, bbuf: ByteBuffer, sel, options):
	"""
	Same as selectionLengthMatcher, but searches for the length +1, +2 and +4.
	"""
	(bufIdx, start, end) = sel
	sellen = end - start + 1
	if sellen == 0: return
	if sellen >= 5:
		for match, desc in findInRange(bbuf, [extendRange(bbuf, (bufIdx, start,start))], intToVarious(sellen+1, sellen+2, sellen+4)):
			editor.highlightMatch(qp, match, "Fuzzy Selection Length as " + desc, QColor("#993399"))

'''
@SelectionHelpers.register(color="#775511", defaultEnabled=False)
def debug_highlightMatchRange(editor: "HexView2", qp: QPainter, bbuf: ByteBuffer, sel, options):
	"""
	Highlights the 16 bytes preceding the selection, because they are searched for other matches

	Internal debug tool

	"""
	editor.highlightMatch(qp, rangeBefore(bbuf, sel), "debug_highlightMatchRange", QColor("#775511"))
'''

@SelectionHelpers.register(color="#666666", defaultEnabled=True)
def highlightSelectionAsLength(editor: "HexView2", qp: QPainter, bbuf:ByteBuffer, sel, options):
	"""
	Parses the current selection as integer and uses the value as a length, to highlight the range with this length
	following the selection.

	First, parsing as big endian is attempted, if the value is too large, little endian is attempted.

	"""
	(bufIdx, start, end)=sel
	end=end+1
	if end-start>8: return
	val = bbuf.getInt(start,end,endianness=">",signed=False)
	if val > 0 and end+val <= len(bbuf):
		editor.highlightMatch(qp, (bufIdx, end, end+val), "Selection As Length (BE)", QColor("#666666"))
		return
	val = bbuf.getInt(start,end,endianness="<",signed=False)
	if val > 0 and end+val <= len(bbuf):
		editor.highlightMatch(qp, (bufIdx, end, end+val), "Selection As Length (LE)", QColor("#666666"))
		return


@SelectionHelpers.register(color="#009999", defaultEnabled=True, options=[
	SettingsField("minLength", "Minimum Selection Length", "int", {"default":2}),
])
def highlightRepetitions(editor: "HexView2", qp: QPainter, bbuf: ByteBuffer, sel, options):
	"""
	Searches for the byte values of the selection in the whole visible buffer, highlighting all occurrences.
	"""
	(bufIdx, selstart, selend) = sel
	sellen = selend - selstart + 1
	if sellen < options.get("minLength", 2): return
	selbytes = bbuf.getBytes(selstart, sellen)
	logging.debug("highlightRepetitions: searching for %r", selbytes)
	(firstBuf, firstOffset), (lastBuf, lastOffset) = editor.visibleRange()
	for i in range(firstBuf, lastBuf + 1):
		start = firstOffset if i == firstBuf else 0
		end = lastOffset if i == lastBuf else len(editor.buffers[i])
		logging.debug("highlightRepetitions: scanning #%d bytes %d-%d",i,start,end)
		for match, desc in findInRange(editor.buffers[i], [(i, start, end)], [(selbytes, "Repetition")]):
			if match == (bufIdx, selstart, selend + 1): continue
			editor.highlightMatch(qp, match, desc, QColor("#009999"))

