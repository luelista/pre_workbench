---
title: Installing PRE Workbench
---

# Install on macOS

Install with `sudo pip3 install pre_workbench`

Run with `prewb` or `python3 -m pre_workbench`

Prebuilt binary wheels exist for macOS 11 on Intel chips. 


# Install on ubuntu

Install dependencies via apt, then install the package via pip.

```
sudo apt install python3-pip qt5-default
sudo pip3 install pre_workbench
prewb
```


# Windows

Windows is currently unsupported / untested. The application should install via pip, 
however for the dependency `PyQtAds`, no binary wheel for windows exists yet. Compiling 
it yourself may or may not work.


