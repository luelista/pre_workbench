---
title: Installing PRE Workbench
---

# Install on macOS

## App Bundle

Download PRE Workbench as an application bundle from [here](https://github.com/luelista/pre_workbench_release/releases). Extract the zip file, right click the `PRE Workbench.app` and choose "Open". The application is not code-signed, therefore you need to allow the execution of untrusted applications in the following dialog.


## Install via pip (Intel)

You need a recent version of pip, the Python package manager. The version supplied with 
macOS might not be sufficient. Therefore run `sudo pip3 install -U pip` first.

Then, install the application with `sudo pip3 install pre_workbench`.

Run with `prewb` or `python3 -m pre_workbench`.

Prebuilt binary wheels exist for macOS 11 on Intel chips. 


## Install via pip (M1)

The Qt framework (version 5), which is used by pre_workbench, is not compatible 
with M1 Macs. However, you can run the application on the Rosetta compatibility layer.

You can do so by creating a copy of `Terminal.app` (call it something like 
`Terminal (Rosetta).app`), click *Get Info* in its context menu, and check 
the *Open using Rosetta* checkbox under *General*.  Afterwards, follow the 
instructions for Intel Macs.


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


