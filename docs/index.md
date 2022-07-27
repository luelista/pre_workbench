---
title: Welcome to PRE Workbench Docs
---

# Documentation

[Installation](install)

[Getting Started](getting-started)

[Syntax Reference](syntax-reference)

[Key Bindings](key-bindings)

[Plugins and Macros](extending)

[Wireshark Dissector Generator](code-generation)


# Features


## Data import
- Load PCAP files
- Load binary files, single or a complete folder as package list
- Load CSV files, using one column as payload (hex/base64 encoded) and the rest as metadata

## Interactive Hexdump
### Heuristics
- Recognize length fields
- highlight matching length fields for selection
- Evaluate selection as length field
- Highlight same content

### Annotations
- color and text highlighting of byte sequences
- Application of the annotations to further packages

### Interactive documentation of procotol structure as grammar
- Description language for binary protocols
- Applying a grammar to multiple packages
- Display of fields from grammar in table

## Other features
### Data inspector
Parse the selection as different data types (Signed/Unsigned Int, Big/Little Endian, ...).

### Search function and execution of external tools
Search one or multiple buffers for a regular expression, e.g. find all ASCII strings 5 byte or longer.

### Project folder
Preferences, widget layout, open files and grammars are stored per project.

### Plugin and macro support
Macros can be added at user-level (~/.config) and at project level (.pre_workbench), and some example macros are
bundled with the application -- to use macros, click "View" > "Tool Windows" > "Macros".
To enable plugin support, configure a plugin directory in the settings dialog. More information in the
[Plugins and Macros documentation](extending) and in the
[release notes](https://github.com/luelista/pre_workbench/releases/tag/0.7.8).
You can find some example plugins on [Github](https://github.com/luelista/prewb_example_plugins).


