import logging
import time

logging.addLevelName(5, "TRACE")
logging.TRACE = 5

class PerfTimer:
    def __init__(self, message, *args):
        self.message = message + " took %f sec"
        self.args = args
    def __enter__(self):
        self.start_time = time.perf_counter()
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start_time
        logging.log(logging.WARN if elapsed > 0.1 else logging.TRACE, self.message, *self.args, elapsed)

def truncate_str(s, length=256):
    s = str(s)
    return s if len(s) < length else s[:length] + "[...]"
