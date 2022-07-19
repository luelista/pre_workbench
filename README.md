# Protocol Reverse Engineering Workbench

PRE Workbench is a software to support researchers in reverse engineering protocols 
and documenting the results.
It supports various sources to import protocol traffic from, helps the
discovery process by displaying different views and heuristic-based 
highlighting on data, and aids in documenting and sharing findings.


## Installation

For installation instructions see [docs/install.md](https://luelista.github.io/pre_workbench/install).


## Development

`make dev` or `python3 setup.py build_ext --inplace` to compile pyx files in place

`make package` builds pip packages and uploads to pypi

`make pyinstaller` builds PyInstaller package (run `pip install pyinstaller` before)

Run `scripts\build_installer.bat` from a cmd.exe in this directory to build the setup.exe on Windows.

## Third Party

### Icons

Fugue Icons, https://p.yusukekamiyamane.com/

Crystal Project, https://store.kde.org/p/1002590/

### Libraries

PyQt5

QScintilla

Lark Parser

Cython

Qt-Advanced-Docking-System

