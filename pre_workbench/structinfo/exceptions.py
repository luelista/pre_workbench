
class parse_exception(Exception):
	def __init__(self, context, msg, cause=None):
		self.offset = context.offset()
		self.context_hexdump = context.hexdump_context(self.offset)
		super().__init__(context.get_path() + ": " + msg + "\n" + self.context_hexdump)
		if cause: self.__cause__ = cause
		self.parse_stack = context.stack


class incomplete(parse_exception):
	def __init__(self, context, need, got):
		super().__init__(context, "incomplete: needed %d, got %d bytes" %(need,got))


class invalid(parse_exception):
	def __init__(self, context, msg="invalid"):
		super().__init__(context, msg)


class value_not_found(parse_exception):
	def __init__(self, context, msg="value_not_found"):
		super().__init__(context, msg)


class spec_error(parse_exception):
	def __init__(self, context, msg):
		super().__init__(context, "spec_error: "+msg)
		self.offending_desc = context.stack[-1].desc

