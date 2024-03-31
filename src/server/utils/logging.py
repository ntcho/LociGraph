from logging import (
    getLevelName,
    basicConfig,
    getLogger,
    WARN,
    DEBUG,
)
from litestar.logging import LoggingConfig

# Logging format
FORMAT = "%(asctime)s | %(filename)s:%(lineno)s | %(levelname)s >>> %(message)s"

# Logging level
LEVEL = DEBUG  # for development
# LEVEL = WARN # for production

# Logging configuration
CONFIG = LoggingConfig(
    root={"level": getLevelName(DEBUG), "handlers": ["console"]},
    formatters={"standard": {"format": FORMAT}},
)

# Configure the Logger
configure = basicConfig

# Return the Logger object
getLogger = getLogger
