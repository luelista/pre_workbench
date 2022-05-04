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
import time

logging.addLevelName(5, "TRACE")
logging.TRACE = 5

class PerfTimer:
    def __init__(self, message, *args):
        self.message = message + " took %f sec"
        self.args = args
    def __enter__(self):
        self.start_time = time.perf_counter()
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        logging.log(logging.WARN if elapsed > 0.1 else logging.TRACE, self.message, *self.args, elapsed)

def truncate_str(s, length=256):
    s = str(s)
    return s if len(s) < length else s[:length] + "[...]"

def get_app_version():
    try:
        import pre_workbench._version
        return pre_workbench._version.version
    except:
        return "dev"
