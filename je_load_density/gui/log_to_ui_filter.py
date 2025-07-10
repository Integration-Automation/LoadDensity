import logging
import queue

locust_log_queue = queue.Queue()

class InterceptAllFilter(logging.Filter):

    def filter(self, record):
        locust_log_queue.put(record.getMessage())
        return False
