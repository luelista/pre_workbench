
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
  - out of band splitting: split by timing (nach X ms pause ist das paket zu ende), split by BREAK condition of serial port
  - ...custom code? (e.g. XML stanzas, ) - XMPP


anzeige annotierter Bytestream im Hexdump:



