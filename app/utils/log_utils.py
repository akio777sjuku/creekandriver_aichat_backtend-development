import os
import sys
import logging
from os import makedirs
from os.path import dirname, exists, join
from logging.handlers import TimedRotatingFileHandler


LOG_ENABLED = True
LOG_TO_CONSOLE = True
LOG_TO_FILE = True
LOG_PATH = './log/'
env = os.getenv("ENVIRONMENT", "development")
if env == 'development':
    CONSQL_LOG_LEVEL = 'DEBUG'
    FILE_LOG_LEVEL = 'DEBUG'
    LOG_LEVEL = 'DEBUG'
elif env == 'staging':
    CONSQL_LOG_LEVEL = 'WARNING'
    FILE_LOG_LEVEL = 'DEBUG'
    LOG_LEVEL = 'DEBUG'
elif env == 'production':
    CONSQL_LOG_LEVEL = 'INFO'
    FILE_LOG_LEVEL = 'WARNING'
    LOG_LEVEL = 'WARNING'

loggers = {}


def get_logger(name: str):
    """
    get logger by name
    :param name: name of logger
    :return: logger
    """
    global loggers
    if loggers.get(name):
        return loggers.get(name)
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # log to the console
    if LOG_ENABLED and LOG_TO_CONSOLE:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level=CONSQL_LOG_LEVEL)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # log to the file
    if LOG_ENABLED and LOG_TO_FILE:
        log_dir = dirname(LOG_PATH)
        if not exists(log_dir):
            makedirs(log_dir)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s")
        save_handler = TimedRotatingFileHandler(
            join(LOG_PATH, f"{name}.log"), when="midnight", interval=1, backupCount=30)
        save_handler.suffix = "%Y-%m-%d"
        save_handler.setFormatter(formatter)
        save_handler.setLevel(level=FILE_LOG_LEVEL)
        logger.addHandler(save_handler)

    # save loggers
    loggers[name] = logger
    return logger
