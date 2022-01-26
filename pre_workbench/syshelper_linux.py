
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

from pathlib import Path
from resource import getpagesize

PAGESIZE = getpagesize()
PATH = Path('/proc/self/statm')

def get_resident_set_size() -> int:
	"""Return the current resident set size in bytes."""
	# statm columns are: size resident shared text lib data dt
	statm = PATH.read_text()
	fields = statm.split()
	return int(fields[1]) * PAGESIZE
