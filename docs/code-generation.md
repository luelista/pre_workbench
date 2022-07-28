# Wireshark Dissector Code Generator

PRE Workbench provides a proof-of-concept code generator for Wireshark Lua dissectors, which supports a subset 
of the protocol grammar language. 

## Supported Features
Types:
* struct
* repeat
* INT / UINT, STRING, BYTES
* named reference to other types defined in the same file

Parameters:
* INT, UINT: endianness
* INT, UINT: magic
* BYTES, INT, UINT: show="hex"
* repeat: times
* STRING, BYTES: size

Expressions:
* references to INT / UINT fields in the same structure or a parent structure 
* basic maths


## Example

Store your protocol grammar either in a project or in a text file `my_proto.txt`:

```
MyProto struct(endianness=">") {
    magic UINT32(magic=2864434397, show="hex", color="#aa0000")
    tlv_count UINT32
    tlvs repeat(times=(tlv_count)) MyTLV
}

MyTLV struct(endianness=">") {
    type UINT16(color="#aaaa00")
    length UINT16(color="#00aa00")
    payload BYTES[length](color="#0000aa")
}
```

Call the code generator as follows:

```
prewb_codegen -P path/to/project -o ~/.local/lib/wireshark/plugins/my_proto.lua --dissector-table udp.port:4321
# or
prewb_codegen -F my_proto.txt -o ~/.local/lib/wireshark/plugins/my_proto.lua --dissector-table udp.port:4321
```

Run Wireshark and load a PCAP file containing protocol samples in a UDP file on port 4321. Alternatively, start a capture on
the loopback device, enter filter `udp.port==4321` and send some samples using netcat:

```
# example with 2 TLVs, one without payload
printf '\xAA\xBB\xCC\xDD\x00\x00\x00\x02\x00\x80\x00\x03\x01\x02\x03\x00\xFF\x00\x00' | nc -u localhost 4321

# example with 0 TLVs
printf '\xAA\xBB\xCC\xDD\x00\x00\x00\x00' | nc -u localhost 4321

# example with wrong magic number
printf '\x00\x11\x22\x33\x00\x00\x00\x00' | nc -u localhost 4321
```

![Results in Wireshark](images/ws-results.png)


## Usage
```
usage: prewb_codegen [-h] [-P DIR] [-F FILENAME] [-e GRAMMAR] [-t TYPENAMES] [-d NAME] [-l LANG] [--dissector-table NAME:KEY] [-o FILENAME]

PRE Workbench - Wireshark Dissector Generator

optional arguments:
  -h, --help            show this help message and exit
  -P DIR, --project DIR
                        Grammar definitions from project directory
  -F FILENAME, --grammar-file FILENAME
                        Grammar definitions from text file
  -e GRAMMAR, --grammar-string GRAMMAR
                        Grammar definitions from command line argument
  -t TYPENAMES, --only-types TYPENAMES
                        Generate code only for specified types (comma-separated list)
  -d NAME, --definition NAME
                        Name of start grammar definition. Uses first if unspecified
  -l LANG, --language LANG
                        Programming language to generate (supported: lua)
  --dissector-table NAME:KEY
                        Register the protocol in the given dissector table, under the given key
  -o FILENAME, --output-file FILENAME
                        Output filename for generated code (default: "-" for stdout)
```


## Limitations

Our current code generator implementation is limited to a subset of possible PRE Workbench protocol grammars. Only  structures, repetitions, named references to other types and a subset of the built-in types are supported, other types like variant, union and switch could not be implemented yet due to time constraints. 
In the expression syntax, only simple expressions consisting of references to fields in the same structure, as well as basic maths, are supported. 
