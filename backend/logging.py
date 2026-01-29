from __future__ import annotations

import atexit
import contextlib
import logging
import sys
from typing import TYPE_CHECKING, Any

from loguru import logger as loguru_logger

from backend import constants
from backend.common.correlation import get_correlation_id

if TYPE_CHECKING:
    from loguru import Logger, Record





class InterceptHandler(logging.Handler):
    """
    Route stdlib logging to loguru with proper level mapping and stack depth.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru_logger.opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


def patch_record(record: Record) -> None:
    extra = record['extra']
    extra.setdefault('correlation_id', get_correlation_id(default='N/A'))


def should_propagate(name: str) -> bool:
    return not any(name in ign for ign in constants.NO_PROPAGATE_LOGGERS)


def get_loguru_options(
    *,
    levelname: str | None = None,
    json_stdout: bool = False,
) -> dict[str, Any]:
    options = {
        'level': levelname or 'DEBUG',
        'format': constants.LOGGER_FORMAT,
        'enqueue': True,
        'backtrace': False,
        'diagnose': False,
    }
    if not json_stdout:
        options.update({
            'sink': sys.stdout,
            'colorize': True,
        })
    else:
        options.update({
            'sink': sys.stdout,
            'serialize': True,
        })

    return options


def configure_logging(
    *,
    json_stdout: bool = False,
    levelname: str | None = None,
) -> None:
    """
    Should be called once at application startup to configure logging.
    """
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).propagate = should_propagate(name)

    loguru_logger.remove()

    levelname = levelname or 'DEBUG'
    handlers: list[Any] = [
        get_loguru_options(levelname=levelname, json_stdout=json_stdout)
    ]

    with contextlib.suppress(ValueError):
        loguru_logger.configure(patcher=patch_record, handlers=handlers)

    atexit.register(loguru_logger.complete)


def get_loguru_logger() -> Logger:
    return loguru_logger
