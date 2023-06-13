import logging
import sys

load_density_logger = logging.getLogger("LoadDensity")
load_density_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
# Stream handler
stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.WARNING)
load_density_logger.addHandler(stream_handler)
# File handler
file_handler = logging.FileHandler("LoadDensity.log")
file_handler.setFormatter(formatter)
load_density_logger.addHandler(file_handler)
