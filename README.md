# Protocol Reverse Engineering Workbench

Install with `pip3 install pre_workbench` or `python3 setup.py install .`

Run with `prewb` or `python3 -m pre_workbench.appmain`



## Install on ubuntu via pip

```
sudo apt install python3-pip qt5-default
sudo pip3 install pre_workbench
prewb
```


## Packaging

`make package` builds pip packages and uploads to pypi

`make pyinstaller` builds PyInstaller package (run `pip install pyinstaller` before)

## Development

`make dev` or `python3 setup.py build_ext --inplace` to compile pyx files in place



## Third Party

### Icons

Fugue Icons, https://p.yusukekamiyamane.com/

Crystal Project, https://store.kde.org/p/1002590/

### Libraries

PyQt5

QScintilla

Lark Parser

Cython

