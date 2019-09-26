
# Vorbereitung - PDUs generieren

ABBS -> annotated bidirectional byte stream

## TCP Teil 1 (packet stream -> bidi. byte stream)
- pcap file lesen
- tcp session auswählen, reassemblen -> ergebnis bidirektionaler bytestream (mit annotations: timestamp, segment)

## UDP
- pcap file lesen
- filter auf z.b. UDP port X setzen, UDP payloads als PDUs ausgeben -> ergebnis bidirektionaler packet stream

## Serial Teil 1 (??? -> ABBS)
- logic trace einlesen (z.b. libsigrok) -> ergebnis bidirektionaler bytestream (mit annotations: timestamp, BREAK conditions)

## anderes paketbasiertes higher level protokoll, z.b. MQTT
- pcap file lesen, MQTT/TCP session auswählen, reassemble, MQTT parsen, ggf nach topic filtern, payload als PDUs verwenden

## TCP, Serial, etc Teil 2 (byte stream -> packet stream)
- jede richtung des bytestream in PDUs aufsplitten, z. B.
  - binary length prefixed, potentially at some offset into the PDU  - almost every binary protocol e.g. MQTT, TLS, ...
  - ascii length prefixed (e.g. netstring) - 
  - split by delimiter (e.g. "\r\n", "\0") - IRC
  - split by begin and end delimiter (e.g. "\x02"->"\x03" or "\x1b"->"\r")
  - out of band splitting: split by timing (nach X ms pause ist das paket zu ende), split by BREAK condition of serial port
  - ...custom code? (e.g. XML stanzas, ) - XMPP


anzeige annotierter Bytestream im Hexdump:






# byteBuffer
- dict<string,string> metadata
- byte[] buffer
- int length
- dict<string,(number,number)> ranges
- dict<string,field> fields
    field = ()

entspricht in etwa dem AnnotatedBuffer

generate by:
load_binary_file(file)
load_tcp_stream(...)
extract_tcp_stream(...)
capture_mitmproxy_stream(...)



# list of byteBuffer
- dict metadata
- byteBuffer[] frames

generate by:
load_pcap_file(file) / parse_pcap(byteBuffer)
split_on_delimiter(byteBuffer, delim)
split_by_length_prefix(packSpec, (meta_names), )
merge_lists_of_byteBuffer(list_of_byteBufer, ...)
concat_lists_of_byteBuffer(list_of_byteBufer, ...)



# szenarien data capture
## reversing BLE IOT hardware (eg. smartlock)
interessante datenströme:
- app<->server (Netzwerk) 
  - pcap ethernet-pakete (frames)  <--  das bekomme ich von libpcap / scapy
    - tcp stream (ABBS)
      - tls pakete (frames)     <--- das bekomme ich von wireshark
        - tls stream (ABBS)   <--- das bekomme ich von mitmproxy
          - APDUs (frames)          <--  das will ich haben ;-)
- app<->device (BLE)
    - hci log (btsnoop)  (frames)
        - ble/att PDUs  (frames)
            - characteristic reads/writes/notifications (frames)  <--- das bekomme ich von wireshark
                - ggf custom transport layer
                  - APDUs (frames) 
- device intern (serial, etc)
    - serial capture (ABBS)



captured ABBS (annotated bi-directional byte stream/buffer)
- 2x ABS (annotated byte stream/buffer)
    - bytes
    - timestamps für bytes / ranges von bytes



