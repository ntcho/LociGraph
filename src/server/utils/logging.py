from loguru import logger

import functools
from time import time
from sys import stderr

from utils.dev import DEV


# export Logger object
log = logger

FORMAT_TIME = "{time:YY-MM-DD_HH-mm-ss_SSS}"
FORMAT = FORMAT_TIME + " | {level: <8} | {file}:{line} {function}() | {message}"

CONFIG = {
    "handlers": [
        {
            "sink": stderr,
            "format": FORMAT,
            "colorize": True,
            "level": "TRACE" if DEV else "INFO",
            "backtrace": DEV,  # only in development
            "diagnose": DEV,  # only in development
        },
        {
            "sink": f"logs/{FORMAT_TIME}.log",
            "format": FORMAT,
            "level": "TRACE",
            "backtrace": True,
            "diagnose": True,
        },
    ],
    "levels": [dict(name="TRACE", color="<dim>")],
}


def log_func(*, entry=True, exit=True, level="TRACE"):
    """Decorator to log function entry and exit.

    Note:
        This decorator uses the `loguru` logger.
        Read more: https://loguru.readthedocs.io/en/stable/resources/recipes.html#logging-entry-and-exit-of-functions-with-a-decorator
    """

    def wrapper(func):
        name = func.__name__

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # logger_ = log.opt(depth=1)

            if entry:
                log.log(level, "Entering '{}' (args={}, kwargs={})", name, args, kwargs)

            start = time()

            result = func(*args, **kwargs)

            end = time()
            d = end - start

            if exit:
                log.log(level, "Exiting '{}' (exec={:f}s, result={})", name, d, result)

            return result

        return wrapped

    return wrapper
