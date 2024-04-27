import functools
from time import time as now
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
    "levels": [
        dict(name="INFO", color="<b><blue>"),
        dict(name="DEBUG", color="<white>"),
        dict(name="TRACE", color="<dim>"),
    ],
}

# default behavior for `log_func` decorator. Set to True to log function entry and exit.
LOG_FUNC_DEFAULT: bool = False  # TODO: set to True on production


def log_func(
    *,
    time=LOG_FUNC_DEFAULT,
    entry=LOG_FUNC_DEFAULT,
    exit=LOG_FUNC_DEFAULT,
    level="TRACE",
):
    """Decorator to log function entry and exit.

    Args:
        time (bool, optional): Log the time taken to execute the function. Defaults to LOG_FUNC_DEFAULT.
        entry (bool, optional): Log the function entry. Defaults to LOG_FUNC_DEFAULT.
        exit (bool, optional): Log the function exit. Defaults to LOG_FUNC_DEFAULT.
        level (str, optional): Log level. Defaults to "TRACE".

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

            start = now()
            result = func(*args, **kwargs)
            end = now()

            if exit:
                exit_str = "\n".join(
                    [
                        f"Exiting '{name}' (exec={(end - start):f}s)",
                        f"\t- result = {repr(result)}" if result is not None else "",
                    ]
                )

                log.log(level, exit_str)
            elif time:
                log.log(level, f"Exiting '{name}' (exec={(end - start):f}s)")

            return result

        return wrapped

    return wrapper


# export Logger object
logger.configure(**CONFIG)

log = logger
