
# Internals

## Core object types
In this section, we describe the main representations of data in the application, which are represented as classes in the implementation. These are also found as essential elements in the user interface.

### Byte Buffers
A **byte buffer** contains a sequence of zero or more bytes (numeric values between zero and 255), and accompanying metadata. Metadata can either apply to the buffer as a whole, or to byte ranges inside the buffer. Annotations, section titles and parsed field values are stored as range-based metadata in the byte buffer object.
Whole-buffer metadata can include a grammar definition name, annotation set name, as well as information provided by the data source, e.g. a packet timestamp or direction.
Byte buffers are either handled individually or as part of a byte buffer list. 
When a binary file is opened in the application, it is loaded into a byte buffer, and displayed individually.

#### Metadata
Byte buffers store five kinds of metadata: 

* A dictionary of metadata provided by the data source, e.g. the packet timestamp from a PCAP file.
* Whether it is marked in the list or not.
* A list of annotations, stored internally in a `RangeList` as described [below](#sec:range-info). 
* The name of the annotation set which is currently applied to the buffer (`annotation_set_name`).

* If the buffer was parsed using a grammar description: the grammar description name (`fi_root_name`), and the parsed fields, as a dictionary accessible by their name (`fields`) and in a tree structure according to the grammar (`fi_tree`).

#### Packet vs. Stream

A ByteBuffer can represent any sequence of bytes, e.g. a packet, a file or a data stream (e.g. a reassembled TCP stream). In the latter case it is often required to split the stream into individual packets. There are multiple ways to do this in PRE Workbench:

* A grammar description can be created, and the `store_into` parameter can be set on the type instance which represents a packet. Once a buffer is parsed with this description, the packets are stored for further use in a new `ByteBufferList`.
* A macro can use the `ByteBuffer` as input data and produce a `ByteBufferList` from it. This allows the user to use arbitrary Python code to split the data.
* Instead of loading the whole stream into a `ByteBuffer`, a custom `DataSource` can be created which splits the data into packets directly while loading it.




### Byte Buffer List

A **byte buffer list** holds an ordered list of byte buffers, accompanied by metadata belonging to the whole list. When a PCAP file is loaded, the packets are loaded into individual byte buffers, which are bundled in a byte buffer list. In this case, individual byte buffers store packet-level metadata like the capture timestamp, while the list stores file-level metadata like interface configuration.
A byte buffer list is displayed using a list-detail interface, with a list of packets, where the columns can display packet metadata, fields and payload, and a detail view which displays the payload of the selected packet in a HexView. 


### Data Source
A **data source** produces one of the objects mentioned above, given some input parameters. For example, the *PCAP file data source* requires a file name as input parameter, and generates a byte buffer list containing all packets from the PCAP file. Data sources can be defined in the application source code, in plugins or in user-defined macros. This allows flexible import of the wide variety of input data that researchers work with.


### Range
**Range** objects represent a consecutive range of bytes in a specific byte buffer and are used in many places throughout the application. For example, the current selection in a HexView is represented by a range, with its *buffer*, *start offset* and *end offset* properties. Furthermore, range objects can store additional metadata like a field name or a background color, and are used to annotate byte ranges in a byte buffer.


<a name="sec:range-info"></a>

## Data Structures for Interval Information
Our application needs to store metadata on ranges of bytes in a buffer. Metadata includes annotations added by the user (colors and text comments), parse results (name and value), and imported metadata from other applications. The byte ranges are allowed to overlap.
There are many possible data structures to store this kind of data. The naive approach would be a simple list of `Range(start, end, metadata)` objects (see `fig:rangelist1`). We started using this approach. However, for painting the HexView display, we need to retrieve the relevant `Range` objects for each painted byte (all objects where `start <= byte index <= end`). If many `Range` objects are stored, retrieval is a performance bottleneck, because we need to scan the whole list (`O(n)` time complexity) for each painted byte. 

A simple optimization would be an array the length of the buffer, where each array element stores a list of references to the `Range` objects relevant to this byte (see `fig:rangelist2`). This is very time efficient (`O(1)` time complexity), but requires a lot of memory for larger files, and is especially memory inefficient for large files with few annotations.

We therefore decided on an approach that compromises between memory and access time. The buffer is divided into chunks of a fixed number of bytes `szelogowskiChunkListConcurrent2022`. For each chunk, a list of references to `Range` objects that have an overlap with the chunk is stored (see `fig:rangelist3`). Therefore, to search for `Range` objects containing a particular byte, only iterate over all Ranges in the chunk of that byte. Thus, the search time complexity is `O(c)`, where `c` is the chunk size.

There are more complex and more efficient data structures to store intervals, for example interval trees `cormenIntroductionAlgorithms2009` and nested containment lists `alekseyenkoNestedContainmentList2007`. However, we found our chunked approach fast enough for a lag-free GUI in regular use of the application. This approach is implemented in the `RangeList` class of our application.


