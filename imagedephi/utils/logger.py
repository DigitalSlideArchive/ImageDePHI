import importlib.resources
import logging
import logging.config
import os

try:
    logging.config.fileConfig(
        "logging.conf"
        if os.path.exists("logging.conf")
        else str(importlib.resources.files("imagedephi") / "logging.conf")
    )
except (FileNotFoundError, KeyError):
    pass

logger = logging.getLogger("root")
