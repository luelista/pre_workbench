---
title: Installing PRE Workbench
---

## Downloads

* PRE Workbench is available on the [Python Package Index as `pre_workbench`](https://pypi.org/project/pre-workbench/).
* Pre-built releases are available on [Github](https://github.com/luelista/pre_workbench/releases).

## Run on NixOS

If you use NixOS and have [flakes enabled](https://nixos.wiki/wiki/Flakes#Enable_flakes_temporarily), you can simply
use the flake:

* `nix run github:luelista/pre_workbench`

* ```
  nix shell github:luelista/pre_workbench
  prewb
  ```


## Install on macOS

### App Bundle

Download PRE Workbench as an application bundle from [here](https://github.com/luelista/pre_workbench/releases). Extract the zip file, right click the `PRE Workbench.app` and choose "Open". The application is not code-signed, therefore you need to allow the execution of untrusted applications in the following dialog.


### Install via pip (Intel)

You need a recent version of pip, the Python package manager. The version supplied with 
macOS might not be sufficient. Therefore run `sudo pip3 install -U pip` first.

Then, install the application with `sudo pip3 install pre_workbench`.

Run with `prewb` or `python3 -m pre_workbench`.

Prebuilt binary wheels exist for macOS 11 on Intel chips. 


### Install via pip (M1)

The Qt framework (version 5), which is used by pre_workbench, is not compatible 
with M1 Macs. However, you can run the application on the Rosetta compatibility layer.

You can do so by creating a copy of `Terminal.app` (call it something like 
`Terminal (Rosetta).app`), click *Get Info* in its context menu, and check 
the *Open using Rosetta* checkbox under *General*.  Afterwards, follow the 
instructions for Intel Macs.


## Install on ubuntu

Install dependencies via apt, then install the package via pip.

```
sudo apt install python3-pip qt5-default
sudo pip3 install pre_workbench
prewb
```


## Install on Windows

On Windows 10 x64, the application can either be installed via pip, or you can 
download a setup.exe from the [Github releases page](https://github.com/luelista/pre_workbench/releases).
Other Windows versions are currently untested.
Installing via pip has the advantage that the command line utitilies can be used.
The setup installs a PyInstaller build which only supports the main GUI appication.


