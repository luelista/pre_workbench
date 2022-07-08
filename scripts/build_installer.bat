
REM run this from the main project folder as "scripts\build_installer.bat"

REM
REM  Requirements: 
REM   -  Python 3.10 or newer
REM   -  pip module: virtualenv must be installed


IF NOT EXIST "venv" virtualenv venv

call venv\Scripts\activate.bat

pip install .
pip install PyInstaller Cython
python setup.py build_ext --inplace

pyinstaller --distpath=dist_pyi --noconfirm "PRE Workbench.spec"

"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" scripts\Win_Installer.iss

deactivate

