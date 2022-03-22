# Grammar files
A grammar file consists of a map of names to type definitions, in the format `name1 definition1 name2 definition2 ...`, each element separated by white-space. The following sections explain all available base types from which the type definitions can be assembled.

```
grammar_file: field*
field: IDENTIFIER type
type: named | struct | repeat | variant | switch | union
```


## named
In any place where a type is expected, a name can be used to reference another type defined in the same file. Many common types of integers, strings, floating-point numbers and network addresses are predefined. For easier adaption, they have the same name as in Wireshark dissectors.

This allows for generalization, because the same type can be references in multiple places (e.g. to define a common header shared by many different packet types). It also can make the grammar easier to read, because special cases can be put away at the end of the file, and the nesting depth can be reduced.
After the type name, parameters configuring parsing or visualization details can be provided in parentheses. This makes it possible to define more generic types, where e.g. the endianness is left open until the usage.

```
UINT32(endianness="<")
--> unsigned integer, 4 byte, little endian.

IPv4
  IP version 4 address, in binary, in network byte order.

UINT_STRING(size_len=2, encoding=">", charset="utf-8")
  character string in UTF-8 encoding, with an unsigned integer, 2 byte, big endian prefix specifing the string length.
  
mytype
```





## `struct`
A struct is defined as an ordered list of named field definitions, where each field has a type.

```
struct: "struct" params "{" (IDENTIFIER type)* "}"
```


```
pascal_string struct {
	length UINT16(endianness=">")
	value STRING(size=(length))
}
```





## `repeat`

```
repeat: "repeat" params type
```


```
int32_array struct(endianness=">") {
	count UINT16
	items repeat(times=(count)) INT32
}
```




## `variant`

```
variant: "variant" params "{" type* "}"
```


```
capture_file variant {
	pcapng_file(endianness=">")
	pcapng_file(endianness="<")
	pcap_file(endianness=">")
	pcap_file(endianness="<")
}

```




## `switch`

```
switch: "switch" expression params "{" ("case" expression ":" type)* "}"
```


```
my_packet struct {
	header struct {
		type UINT8
	}
	payload switch (header.type) {
		case (1): payload_1
		case (2): payload_2
	}
}
```




## `union`

```
union: "union" params "{" (IDENTIFIER type)* "}"
```

```
u_s union {
	unsigned UINT16
	signed INT16
}
```




## `bits`

```
bits: "bits" params "{" (IDENTIFIER ":" number)* "}"
```

```
header bits {
	TRX : 15
	res_1 : 1
	MID : 10
	res_2 : 2
	A : 1
	SEQ_hi : 3
	LEN : 15
	SEQ_lo : 8
	GROUP : 6
	res_3 : 3
}
```

