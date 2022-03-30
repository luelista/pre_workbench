# Grammar files
A grammar file consists of a map of names to type definitions, in the format `name1 definition1 name2 definition2 ...`, each element separated by white-space. The following sections explain all available base types from which the type definitions can be assembled.

```
grammar_file: field*
field: IDENTIFIER type
type: named | struct | repeat | variant | switch | union | bits

params: ("(" [parampair ("," parampair)*] ")")?
parampair: IDENTIFIER "=" value
```

# Parameters

Some parameters are recognized on all types, where the `params` element is accepted. Other parameters are recognized on 
specific types only, but can also be declared on any surrounding container type, causing them to cascade to the children
(e.g., declaring `endianness` on a struct specifies the endianness for all struct elements). 

| parameter | type | description |
| ------------- | ------- | --- |
| ignore_errors | Boolean | If true, all errors which may occur during parsing this element or it's children are ignored. |
| reassemble_into | list (Expression or string) |  |
| store_into | list (Expression or string) |  |
| segment_meta |  | experimental??? |



# Type Definitions

## named

```
named: IDENTIFIER params
```

In any place where a type is expected, a name can be used to reference another type defined in the same file. Many common types of integers, strings, floating-point numbers and network addresses are predefined. For easier adaption, they have the same name as in Wireshark dissectors.

This allows for generalization, because the same type can be references in multiple places (e.g. to define a common header shared by many different packet types). It also can make the grammar easier to read, because special cases can be put away at the end of the file, and the nesting depth can be reduced.
After the type name, parameters configuring parsing or visualization details can be provided in parentheses. This makes it possible to define more generic types, where e.g. the endianness is left open until the usage.

```
UINT32(endianness="<")
--> unsigned integer, 4 byte, little endian.

IPv4
--> IP version 4 address, in binary, in network byte order.

UINT_STRING(size_len=2, encoding=">", charset="utf-8")
--> character string in UTF-8 encoding, with an unsigned integer, 2 byte, big endian prefix specifing the string length.
  
mytype
--> custom type declared elsewhere
```


| parameter | type | description |
| ------------- | ------- | --- |
| endianness    | String  | "<" (Little endian) or ">" (Big endian). **Required** by some built-in named types (multibyte int and floats). |
| charset       | String  | [Python charsets, e.g. "utf-8"][charsets]. **Required** by all string types. |
| unit          | String  | "s", "ms", "us". Optional for ABSOLUTE_TIME, guessed if absent. |
| magic         | ???     | If specified, the field is only valid if its value matches the magic. |
| size          | int expression  | Optional for STRING and BYTES fields, the rest of the parsing unit is matched if absent. |
| size_len      | int expression  | **Required** for UINT_STRING and UINT_BYTES |
| parse_with    | named   | Usually used on BYTES or UINT_BYTES fields, causes the value to be parsed as a child parsing unit. This allows to run the child parser with a fixed length, by specifying `size` or using UINT_BYTES. |


## `struct`
A struct is defined as an ordered list of named field definitions, where each field has a type.

```
struct: "struct" params "{" (IDENTIFIER type)* "}"
```


```
pascal_string struct {
	length UINT16(endianness=">")
	value STRING(size=(length), charset="utf8")
}
# note: a pascal_string could be defined more easily using the UINT_STRING built-in, as shown above
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



| parameter | type | description |
| ------------- | ------- | --- |
| times       | int expression  |  |
| until       | int expression |  |
| until_invalid       | boolean  |  |


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
header bits(endianness="<") {
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


| parameter | type | description |
| ------------- | ------- | --- |
| endianness    | String  | "<" (Little endian) or ">" (Big endian). |




[charsets]: <https://docs.python.org/3/library/codecs.html#standard-encodings>
