# Kaitai struct

```
meta:
  id: tcp_segment
  title: TCP (Transmission Control Protocol) segment
  xref:
    rfc:
      - 793
      - 1323
    wikidata: Q8803
  license: CC0-1.0
  endian: be
doc: |
  TCP is one of the core Internet protocols on transport layer (AKA
  OSI layer 4), providing stateful connections with error checking,
  guarantees of delivery, order of segments and avoidance of duplicate
  delivery.
seq:
  - id: src_port
    type: u2
  - id: dst_port
    type: u2
  - id: seq_num
    type: u4
  - id: ack_num
    type: u4
  - id: b12
    type: u1
  - id: b13
    type: u1
  - id: window_size
    type: u2
  - id: checksum
    type: u2
  - id: urgent_pointer
    type: u2
  - id: body
    size-eos: true
```



#ScaPy
```python
class TCP(Packet):
    name = "TCP"
    fields_desc = [ShortEnumField("sport", 20, TCP_SERVICES),
                   ShortEnumField("dport", 80, TCP_SERVICES),
                   IntField("seq", 0),
                   IntField("ack", 0),
                   BitField("dataofs", None, 4),
                   BitField("reserved", 0, 3),
                   FlagsField("flags", 0x2, 9, "FSRPAUECN"),
                   ShortField("window", 8192),
                   XShortField("chksum", None),
                   ShortField("urgptr", 0),
                   TCPOptionsField("options", "")]
````


#SynalizeIt
```xml
        <structure name="IPv4 TCP Packet" id="328" repeatmin="0" extends="id:332">
            <number name="ip.version" id="411" type="integer"/>
            <number name="ip.proto" id="420" type="integer">
                <fixedvalues>
                    <fixedvalue name="TCP" value="6"/>
                </fixedvalues>
            </number>
            <structure name="ip.src" id="421">
                <number name="ip.src_octet_1" id="423" type="integer"/>
                <number name="ip.src_octet_2" id="424" type="integer"/>
                <number name="ip.src_octet_3" id="425" type="integer"/>
                <number name="ip.src_octet_4" id="426" type="integer"/>
            </structure>
            <structure name="ip.dst" id="428">
                <number name="ip.dst_octet_1" id="429" type="integer"/>
                <number name="ip.dst_octet_2" id="430" type="integer"/>
                <number name="ip.dst_octet_3" id="431" type="integer"/>
                <number name="ip.dst_octet_4" id="432" type="integer"/>
            </structure>
            <number name="tcp.srcport" id="434" fillcolor="5C82FF" type="integer" length="2"/>
            <number name="tcp.dstport" id="435" fillcolor="48F94F" type="integer" length="2"/>
            <number name="tcp.seq" id="436" fillcolor="9F659D" type="integer" length="4"/>
            <number name="tcp.ack" id="437" fillcolor="9F659D" type="integer" length="4"/>
            <number name="tcp.hdr_len" id="438" fillcolor="9F659D" type="integer" length="4" lengthunit="bit"/>
            <binary name="tcp.reserved" id="439" fillcolor="9F659D" length="3" lengthunit="bit"/>
            <binary name="tcp.flags" id="440" fillcolor="9F659D" length="9" lengthunit="bit"/>
            <number name="tcp.window_size_value" id="441" fillcolor="9F659D" type="integer" length="2"/>
            <number name="tcp.checksum" id="442" fillcolor="9F659D" type="integer" length="2"/>
            <number name="tcp.urgent_pointer" id="443" fillcolor="9F659D" type="integer" length="2"/>
            <binary name="ip.data" id="444" fillcolor="9F659D" length="remaining"/>
        </structure>
```
