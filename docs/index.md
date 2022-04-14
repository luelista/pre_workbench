---
title: Welcome to PRE Workbench Docs
---

# Documentation

[Installation](install)

[Getting Started](getting-started)

[Syntax Reference](syntax-reference)

[Key Bindings](key-bindings)

# Features


## Data import
- Load PCAP files
- load binary files, single or a complete folder as package list

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

##Other features
### Data inspector
Parse the selection as different data types (Signed/Unsigned Int, Big/Little Endian, ...).

### Search function and execution of external tools
Search one or multiple buffers for a regular expression, e.g. find all ASCII strings 5 byte or longer.

### Project folder
Preferences, widget layout, open files and grammars are stored per project.
