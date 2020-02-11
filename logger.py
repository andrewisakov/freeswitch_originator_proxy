import os
import logging
from logging.handlers import TimedRotatingFileHandler


def rotating_log(path, name, log_level=logging.DEBUG):
    # global logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # add a rotating handler
    formatter = logging.Formatter(
        '%(asctime)s %(module)s [%(lineno)s] %(levelname)s %(message)s')
    dir_name = os.path.dirname(path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    handler = TimedRotatingFileHandler(path, when='midnight', backupCount=5)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
