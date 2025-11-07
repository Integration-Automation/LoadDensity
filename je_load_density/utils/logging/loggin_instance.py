import logging
import sys
from logging.handlers import RotatingFileHandler


class LoadDensityLogger:
    """
    封裝日誌系統
    Encapsulated logging system with rotating file handler
    """

    def __init__(self,
                 logger_name: str = "LoadDensity",
                 log_file: str = "LoadDensity.log",
                 max_bytes: int = 1024 * 1024 * 1024,  # 1GB
                 backup_count: int = 5):
        """
        初始化 Logger
        Initialize logger

        :param logger_name: Logger 名稱 (Logger name)
        :param log_file: 日誌檔案名稱 (Log file name)
        :param max_bytes: 單一檔案最大大小 (Max file size in bytes)
        :param backup_count: 保留檔案數量 (Number of backup files)
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )

        # Stream handler (輸出到 stderr)
        stream_handler = logging.StreamHandler(stream=sys.stderr)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING)

        # Rotating file handler (檔案大小限制 + 輪替)
        file_handler = RotatingFileHandler(
            filename=log_file,
            mode="a",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # 加入 handlers
        self.logger.addHandler(stream_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """取得 logger 實例 (Get logger instance)"""
        return self.logger


load_density_logger = LoadDensityLogger().get_logger()
