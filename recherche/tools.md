list of binary parsing frameworks/libraries
- A list of generic tools for parsing binary data structures, such as file formats, network protocols or bitstreams
- https://github.com/dloss/binary-parsing


Hilti / BinPAC / Spicy
- Traffic inspection DSL for bro/zeek; parser generator 
- Sommer et al. HILTI: An Abstract Execution Environment forDeep, Stateful Network Traffic Analysis
- Sommer et al. Spicy: A Unified Deep Packet Inspection Frameworkfor Safely Dissecting All Your Data

- http://www.icir.org/hilti/
- BinPAC++ Demo by Robin Sommer  https://www.youtube.com/watch?v=3sQ6thi_BR0&feature=youtu.be



pyreshark
- Pyreshark is an extension for wireshark which allows the user to write dissectors in python.
- same as with lua dissector, it seems necessary to restart wireshark for every change to the dissector.
- https://github.com/ashdnazg/pyreshark/wiki/Writing-Dissectors
- field definitions are similar to scapy

Hexinator / SynalizeIt
- (closed source)
- hex editors with "Universal parsing" support based on XML grammar files.
- sample grammars: https://www.synalysis.net/formats.xml
- https://hexinator.com/
- grammar can be created with GUI
- select bytes in hex view, right click, "insert binary/structure/number/etc"
- tutorial with screenshots of gui: https://www.synalysis.net/tutorial-decode-a-png-file.html

netzob
- https://netzob.readthedocs.io/en/latest/tutorials/discover_features.html#discover-features
- tutorial: https://blog.amossys.fr/How_to_reverse_unknown_protocols_using_Netzob.html
- Bossert, Guihery. The future of protocol reversing and simulation with Netzob https://fahrplan.events.ccc.de/congress/2012/Fahrplan/attachments/2222_netzob.pdf

KaiTai struct
- http://kaitai.io/
- syntax:
- https://formats.kaitai.io/tcp_segment/index.html
- https://formats.kaitai.io/pcap/index.html


- einige interessante antworten https://stackoverflow.com/questions/18270311/dynamic-recognition-and-handling-of-protocol-data-units-in-bytestream
    - "next generation network analyzer" ??? https://i.stack.imgur.com/3iF6s.png



# Hex editors


HexEd.It 
- Javascript hex editor mit nettem Data Inspector (closed source)
- https://hexed.it/?hl=en

IceBuddha
- Javascript hex editor
- "Generic binary file parser" mit python-skripten die im browser ausgeführt werden mit Skulpt (http://skulpt.org/)
- http://icebuddha.com/
- https://github.com/0xdabbad00/icebuddha

HexWorks
- Javascript hex editor, owner drawn on canvas
- simple color highlighting by drag and click, can apply colorization to other files
- simple binary diff
- http://hex-works.com/eng
- open source https://github.com/michbil/hex-works
