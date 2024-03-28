from logging import getLevelName, INFO, DEBUG
from litestar.logging import LoggingConfig

FORMAT = "%(asctime)s | %(filename)s:%(lineno)s | %(levelname)s >>> %(message)s"
CONFIG = LoggingConfig(
    root={"level": getLevelName(DEBUG), "handlers": ["console"]},
    formatters={"standard": {"format": FORMAT}},
)
