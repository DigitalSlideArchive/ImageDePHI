import logging
import logging.config

logging.config.fileConfig("logging.conf")

logger = logging.getLogger("root")
