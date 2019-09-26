
def get_current_rss():
	import os
	import psutil
	process = psutil.Process(os.getpid())
	return process.memory_info().rss
