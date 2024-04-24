import functools
from time import time
from sys import stderr

from loguru import logger

from utils.dev import DEV

# format for log messages
FORMAT = "<green>{time:YY-MM-DD HH:mm:ss.SSS}</> | <level>{level: <8}</> | <cyan>{file}</>:<cyan>{line}</> | {function} | <level>{message}</>"

# format for log filenames
FORMAT_LOG_FILENAME = "{time:YY-MM-DD_HH-mm-ss_SSS}"

# loguru configuration
CONFIG = {
    # Read more: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.configure
    "handlers": [
        {
            "sink": stderr,
            "format": FORMAT,
            "level": "TRACE" if DEV else "INFO",
            "backtrace": DEV,  # only in development
            "diagnose": DEV,  # only in development
        },
        {
            "sink": f"logs/{FORMAT_LOG_FILENAME}.log",
            "format": FORMAT,
            "level": "TRACE",
            "backtrace": True,
            "diagnose": True,
        },
    ],
    "levels": [dict(name="TRACE", color="<dim>")],
}

# default behavior for `log_func` decorator. Set to True to log function entry and exit.
LOG_FUNC_DEFAULT: bool = False  # TODO: set to True on production


def log_func(*, entry=LOG_FUNC_DEFAULT, exit=LOG_FUNC_DEFAULT, level="TRACE"):
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
                args_str = [f"\t- arg{i} = {repr(a)}" for i, a in enumerate(list(args))]
                kwargs_str = [f"\t- {k} = {repr(v)}" for k, v in kwargs.items()]

                entry_str = "\n".join(
                    [
                        f"Entering '{name}'",
                        "\n".join(args_str + kwargs_str),
                    ]
                )

                log.log(level, entry_str)

            start = time()
            result = func(*args, **kwargs)
            end = time()

            if exit:
                exit_str = "\n".join(
                    [
                        f"Exiting '{name}' (exec={(end - start):f}s)",
                        f"\t- result = {repr(result)}" if result is not None else "",
                    ]
                )

                log.log(level, exit_str)

            return result

        return wrapped

    return wrapper


# export Logger object
logger.configure(**CONFIG)

log = logger
