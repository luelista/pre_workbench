


parse_struct_template = """
"""

file_template = """
-- {proto_abbrev} protocol example
-- declare our protocol
{proto_abbrev}_proto = Proto("{proto_abbrev}","Trivial Protocol")
-- create a function to dissect it
function {proto_abbrev}_proto.dissector(buffer,pinfo,tree)
    pinfo.cols.protocol = "TRIVIAL"
    local subtree = tree:add({proto_abbrev}_proto,buffer(),"Trivial Protocol Data")
    subtree:add(buffer(0,2),"The first two bytes: " .. buffer(0,2):uint())
    subtree = subtree:add(buffer(2,2),"The next two bytes")
    subtree:add(buffer(2,1),"The 3rd byte: " .. buffer(2,1):uint())
    subtree:add(buffer(3,1),"The 4th byte: " .. buffer(3,1):uint())
end
"""
