import logging

from pre_workbench import app
from pre_workbench.structinfo.parsecontext import AnnotatingParseContext, FormatInfoContainer


class BytebufferAnnotatingParseContext(AnnotatingParseContext):
	def __init__(self, format_infos: FormatInfoContainer, bbuf):
		super().__init__(format_infos, bbuf.buffer)
		self.bbuf = bbuf

	def pack_value(self, value):
		from pre_workbench.structinfo.format_info import FormatInfo
		range = super().pack_value(value)
		range.metadata.update({ 'name': self.get_path(), 'pos': self.top_offset(), 'size': self.top_length(), '_sdef_ref': self.stack[-1].desc, 'show': str(value) })
		fi = self.stack[-1].desc
		if isinstance(fi, FormatInfo):
			range.metadata.update(fi.extra_params(context=self))
		elif isinstance(fi, dict):
			range.metadata.update(fi)
		self.bbuf.addRange(range)
		return range

def apply_grammar_on_bbuf(bbuf, grammarDefName, on_new_subflow_category=None):
	if not grammarDefName: return
	# clear out the old ranges from the last run, but don't delete ranges from other sources (e.g. style, bidi-buf)
	bbuf.setRanges(bbuf.matchRanges(doesntHaveMetaKey='_sdef_ref'))
	bbuf.fi_container = app.CurrentProject.formatInfoContainer
	parse_context = BytebufferAnnotatingParseContext(bbuf.fi_container, bbuf)
	parse_context.on_new_subflow_category = on_new_subflow_category
	bbuf.fi_root_name = grammarDefName
	bbuf.fi_tree = parse_context.parse(grammarDefName)
	if parse_context.failed:
		logging.exception("Failed to apply grammar definition", exc_info=parse_context.failed)
		logging.getLogger("DataSource").error("Failed to apply grammar definition: " + str(parse_context.failed))
