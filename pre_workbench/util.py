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
import sys, os.path

from PyQt5.QtCore import QThread, pyqtSignal

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

class SimpleThread(QThread):
    resultReturned = pyqtSignal(object)
    def __init__(self, parent, thread_fn, finish_fn):
        super().__init__(parent)
        self.thread_fn = thread_fn
        self.resultReturned.connect(finish_fn)
        self.start()
    def run(self) -> None:
        try:
            self.resultReturned.emit(self.thread_fn())
        except:
            logging.exception("Exception in SimpleThread")


# from here: https://github.com/samdroid-apps/werkzeug/blob/268cad0016bcbccff8a8bb9190d39fdd12dc13d2/werkzeug/_reloader.py#L59
def get_exe_for_reloading():
    """Returns the executable. This contains a workaround for windows
    if the executable is incorrectly reported to not have the .exe
    extension which can cause bugs on reloading.  This also contains
    a workaround for linux where the file is executable (possibly with
    a program other than python)
    """
    rv = [sys.executable]
    py_script = os.path.abspath(sys.argv[0])

    if os.name == 'nt' and not os.path.exists(py_script) and \
       os.path.exists(py_script + '.exe'):
        py_script += '.exe'

    windows_workaround = (
        os.path.splitext(rv[0])[1] == '.exe'
        and os.path.splitext(py_script)[1] == '.exe'
    )
    nix_workaround = os.path.isfile(py_script) and os.access(py_script, os.X_OK)

    if windows_workaround or nix_workaround:
        rv.pop(0)

    rv.append(py_script)
    return rv

