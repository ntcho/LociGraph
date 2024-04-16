from utils.logging import log, log_func

from dtos import Event

a = Event()
b = Event()


@log_func()
def z(x):
    log.info("test")
    log.warning("test")
    log.error("test")
    return x**2


@log_func()
def x(a, b, asdf):
    return b, a


x(a, b, asdf=b)
