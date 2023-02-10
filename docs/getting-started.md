---
title: Getting Started
---

## First Run

* After [Installation](install.md), run PRE Workbench by double-clicking the program icon (Windows and macOS) or running the `prewb` command (Linux).
* On first run, you'll be asked to choose or create a project directory. Files from this directory will be available to be loaded into the app. PRE Workbench will create a project database file named `.pre_workbench` in this folder, but nothing else will be touched in the folder. Later on, you can change the directory from the main menu.
* tbd.


## Video Walkthrough

<iframe width="830" height="540" src="https://www.youtube.com/embed/U3op5UreV1Q" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>


## Command Line Interface

Although PRE Workbench is mainly a GUI application, there are some command line arguments to
the main application, and there is a separate tool to run parsers directly from the command
line.

### prewb

#### Usage
Just run `prewb` to start the GUI application.

Pass a directory path to start with this specific project, or run `prewb --choose-project`
to force the project chooser dialog to appear.

If the configuration file got messed up, run `prewb --reset-config`. Note that this deletes
all application-wide configuration. Project-specific configuration will be left alone.
To reset these, delete or rename the `.pre_workbench` file from your project directory.

You can also specify various debug options with --log-level, --log-config and --gc-debug.

```
usage: prewb [-h] [--reset-config] [--log-level {TRACE,DEBUG,INFO,WARNING,ERROR}] [--log-config FILE] [--plugins-dir DIR] [--gc-debug] [--choose-project] [DIR]

Protocol Reverse Engineering Workbench

positional arguments:
  DIR                   Project directory

optional arguments:
  -h, --help            show this help message and exit
  --reset-config        Reset the configuration to defaults
  --log-level {TRACE,DEBUG,INFO,WARNING,ERROR}
                        Set the log level
  --log-config FILE     Load detailed logging config from file
  --plugins-dir DIR     Load all Python files from this folder as plugins
  --gc-debug            Print debug output from garbage collector
  --choose-project      Force the project directory chooser to appear, instead of opening the last project
```

On Windows, the `prewb` command runs the application in GUI mode, preventing command line output. To see the log output,
use the `prewb_c` command which runs in console mode.

### prewb_parse

#### Usage
```
usage: prewb_parse [-h] [-P DIR] [-F FILENAME] [-e GRAMMAR] [-d NAME] [-i FILENAME] [-x HEXSTRING] [--json]

Protocol Reverse Engineering Workbench CLI Parser

optional arguments:
  -h, --help            show this help message and exit
  -P DIR, --project DIR
                        Grammar definitions from project directory
  -F FILENAME, --grammar-file FILENAME
                        Grammar definitions from text file
  -e GRAMMAR, --grammar-string GRAMMAR
                        Grammar definitions from command line argument
  -d NAME, --definition NAME
                        Name of start grammar definition. Uses first if unspecified
  -i FILENAME, --input-file FILENAME
                        File to parse
  -x HEXSTRING, --input-hex HEXSTRING
                        Hex string to parse
  --json                Print json output
```

#### Examples
```
$ prewb_parse -e "_ struct {foo UINT8 bar UINT8}" -x "1122"
{
    "foo": 17,
    "bar": 34
}

$ prewb_parse -e "_ repeat UINT8" -x "11223344"
[
    17,
    34,
    51,
    68
]
```


### prewb_codegen

### xdrmap

Converts between the binary [XDRmap file format](internals.md#xdrmap) and YAML.

#### Usage
```
usage: xdrmap [-h] [-m HEXSTR] [-D] [-E] [-i INPUT] [-v]

XDRmap encoder/decoder

optional arguments:
  -h, --help            show this help message and exit
  -m HEXSTR, --magic HEXSTR
                        Magic value prefix, encoded as hex string
  -D, --decode          Decodes input from XDRmap to YAML
  -E, --encode          Encodes input from YAML to XDRmap
  -i INPUT, --input INPUT
                        Input file (default: "-" for stdin)
  -v, --verbose         Enable verbose logging to stderr
```

