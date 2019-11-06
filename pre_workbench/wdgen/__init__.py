


port_definitions_template = """
#define {proto_abbrev}_PORT_{lower_proto_abbrev} {port}
"""

hf_id_definitions_template = """static int hf_{proto_abbrev}_{field_name} = -1;
"""


# struct header_field_info {
#     const char      *name;
#     const char      *abbrev;
#     enum ftenum     type;
#     int             display;
#     const void      *strings;
#     guint64         bitmask;
#     const char      *blurb;
#     .....
# };

hf_info_template = """
		{ &hf_{proto_abbrev}_{field_name}, {
			"Data", "{proto_abbrev}.{field_name}", FT_STRING, BASE_NONE,
			NULL, 0, NULL, HFILL }},"""

file_template = """
/* packet-{proto_abbrev}.c
 * Routines for {proto_abbrev} packet dissection
 * {main_comment}
 */

#include "config.h"

#include <epan/packet.h>

{port_definitions}

void proto_register_{proto_abbrev}(void);
void proto_reg_handoff_{proto_abbrev}(void);

static int proto_{proto_abbrev} = -1;

{hf_id_definitions}

static gint ett_{proto_abbrev} = -1;

/* dissect_{proto_abbrev} - dissects {proto_abbrev} packet data
 * tvb - tvbuff for packet data (IN)
 * pinfo - packet info
 * proto_tree - resolved protocol tree
 */
static int
dissect_{proto_abbrev}(tvbuff_t *tvb, packet_info *pinfo, proto_tree *tree, void* dissector_data _U_)
{
	proto_tree* {proto_abbrev}_tree;
	proto_item* ti;
	guint8* data;
	guint32 len;

	col_set_str(pinfo->cinfo, COL_PROTOCOL, "{proto_short_name}");
	col_set_str(pinfo->cinfo, COL_INFO, "{proto_short_name}");

	ti = proto_tree_add_item(tree, proto_{proto_abbrev}, tvb, 0, -1, ENC_NA);
	{proto_abbrev}_tree = proto_item_add_subtree(ti, ett_{proto_abbrev});

	len = tvb_reported_length(tvb);
	data = tvb_get_string_enc(wmem_packet_scope(), tvb, 0, len, ENC_ASCII);

	proto_tree_add_string_format({proto_abbrev}_tree, hf_{proto_abbrev}_data, tvb, 0,
		len, "Data", "Data (%u): %s", len, data);

/*	proto_tree_add_item({proto_abbrev}_tree, hf_{proto_abbrev}_data, tvb, 0, -1, ENC_ASCII|ENC_NA); */
	return tvb_captured_length(tvb);
}

void
proto_register_{proto_abbrev}(void)
{
	static hf_register_info hf[] = {
{hf_info}
		};

	static gint *ett[] = {
		&ett_{proto_abbrev},
	};

	proto_{proto_abbrev} = proto_register_protocol("{proto_name}", "{proto_short_name}",
	    "{proto_abbrev}");
	proto_register_field_array(proto_{proto_abbrev}, hf, array_length(hf));
	proto_register_subtree_array(ett, array_length(ett));
}

void
proto_reg_handoff_{proto_abbrev}(void)
{
	dissector_handle_t {proto_abbrev}_handle;

	{proto_abbrev}_handle = create_dissector_handle(dissect_{proto_abbrev}, proto_{proto_abbrev});
	dissector_add_uint_with_preference("udp.port", CHARGEN_PORT_UDP, {proto_abbrev}_handle);
	dissector_add_uint_with_preference("tcp.port", CHARGEN_PORT_TCP, {proto_abbrev}_handle);
}

/*
 * Editor modelines  -  https://www.wireshark.org/tools/modelines.html
 *
 * Local variables:
 * c-basic-offset: 8
 * tab-width: 8
 * indent-tabs-mode: t
 * End:
 *
 * vi: set shiftwidth=8 tabstop=8 noexpandtab:
 * :indentSize=8:tabSize=8:noTabs=false:
 */
"""