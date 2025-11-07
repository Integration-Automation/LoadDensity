import logging
import queue

# 建立一個佇列，用來存放攔截到的日誌訊息
# Create a queue to store intercepted log messages
log_message_queue: queue.Queue[str] = queue.Queue()


class InterceptAllFilter(logging.Filter):
    """
    攔截所有日誌訊息並存入佇列
    Intercept all log messages and store them into a queue

    此 Filter 可用於將 logging 模組的輸出導向 GUI 或其他處理流程。
    This filter can be used to redirect logging outputs to a GUI or other processing pipelines.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        攔截日誌紀錄並存入佇列
        Intercept log record and put it into the queue

        :param record: logging.LogRecord 物件 (Log record object)
        :return: False → 阻止訊息繼續傳遞到其他 Handler
                 False → Prevents the message from propagating to other handlers
        """
        # 只存放訊息文字，也可以改成存整個 record 以保留更多資訊
        # Only store the message text; alternatively, store the whole record for more details
        log_message_queue.put(record.getMessage())
        return False