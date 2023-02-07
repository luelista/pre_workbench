
# Data Sources

In the application source code and in plugins, data sources are implemented as Python classes inheriting from either `DataSource` or `SyncDataSource`. The former can provide data asynchronously, allowing for live capture of data, for example by calling a third-party process or by reading from the network. The latter are easier to implement and only load data synchronously, which is most useful to implement data importers for local files of different types. User-defined macros always work synchronously, they are just a Python code snippet which is given all input parameters as predefined variables and needs to store the generated `ByteBuffer` or `ByteBufferList` object in the `output` variable.


## PCAP Files
The predefined *PCAP file data source* simply loads all packets from a local PCAP file by directly parsing the file contents. It supports the PCAP and PCAPNG file types in big-endian and little-endian byte order.


## CSV Files
The *CSV file data source* loads a file in the *CSV* format into a `ByteBufferList`, so that each row is converted to a `ByteBuffer`. 
One column of the CSV file has to be selected to provide the payload, which can be decoded from a hexadecimal or Base64 string. All remaining columns are stored as packet metadata in the ByteBuffer. The user can configure the exact format of the file, specifying the column delimiters, quote characters, and whether a header row is present or not.


## Binary Files
Raw binary files can be imported using two different predefined data sources, the binary file and directory of binary files data sources.
The *binary file data source* simply loads binary data from a file into a `ByteBuffer` without any modification. No metadata is generated.
The *directory of binary files data source* scans a local directory using a *glob*-style search pattern, and loads all matching files into a `ByteBufferList`. The file names and modification timestamps are stored as packet metadata. 


## Macro
As a demonstration for the macro capabilities, and as a template for users who want to implement their own, we implemented three different macro data sources: One which imports a JSON file as a `ByteBufferList`, another that imports an Intel HEX file as `ByteBuffer`, as well as one that imports a binary file splitted into packets using static delimiters as a `ByteBufferList`.

The *JSON file data source* works similar to the CSV one. Instead of rows in the CSV file, there needs to be a JSON array at the root level. Each array item must be a dictionary, each of which is converted into a `ByteBuffer`, where one entry is used as the payload and all others are stored as metadata. If the user needs to import a different JSON structure, they can copy the macro to their project and adapt the code accordingly.


## Data Import From Wireshark
We also want to harness the multitude of existing Wireshark dissectors. To this end, we allow the user to import packets via Wireshark's command-line utility, `tshark`. It provides a feature to export traces with full dissector output in the *PDML*, an XML-based file format. It allows live captures, as well as importing existing PCAP files, so we implemented the *Live capture via Tshark* and *PCAP file via Tshark* data sources.

The PDML format is structured in the same way as the tree view in Wireshark's GUI. As we also support a tree structure for the protocol fields in our `ByteBuffer`s, we can store the dissector output almost verbatim in our internal data structures. PDML also contains byte range information on the fields, so we can also store and display them as annotations.

This allows the user to fully use our GUI with data imported from Wireshark, seeing the existing annotations from the dissector and adding their own ones later on.

