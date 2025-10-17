

"""
Setup and configuration functions for the application logger,
which uses loguru under the hood. Supports both stdout logging
and structured file logging and stdlib logs are redirected to loguru.

NOTE:
Loguru for some reason doesn't like being type hinted (importing Logger, Record),
which is why they are imported as such.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger as loguru_logger

from app.core.correlation_id import get_correlation_id

if TYPE_CHECKING:
    from loguru import Logger, Record

    from app.core.configs import LoggerConfig


def _create_file_sink(name: str) -> str:
    directory = Path('logs')
    directory.mkdir(parents=True, exist_ok=True)
    return str(directory / f'{name}_{{time:YYYY-MM-DD}}.log')


def _correlation_id_patch(record: Record) -> None:
    """
    A patch function to ensure correlation_id is always present
    in the loguru record extra fields.

    Parameters
    ----------
    record : 'Record'
        The loguru record to patch.
    """
    cor_id = get_correlation_id()
    if 'correlation_id' not in record['extra']:
        record['extra']['correlation_id'] = cor_id or 'N/A'


class InterceptHandler(logging.Handler):
    '''
    Ensures stdlib logs go through loguru allowing
    for the use of the standard logging library in
    3rd party libraries while still having all logs
    '''

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def add_stream_loggers(config: LoggerConfig) -> None:
    '''
    Adds stream loggers to the loguru logger instance,
    for both stdout and stderr.
    '''
    stream_config = {
        'format': config.format.strip(),
        'colorize': True,
        'enqueue': True,
        'backtrace': True,
        'diagnose': False,
    }

    def _stdout_filter(record: Record) -> bool:
        return record['level'].no < logging.ERROR

    def _stderr_filter(record: Record) -> bool:
        return record['level'].no >= logging.ERROR

    loguru_logger.add(
        sys.stdout, level=config.level, filter=_stdout_filter, **stream_config
    )
    loguru_logger.add(
        sys.stderr, level=logging.ERROR, filter=_stderr_filter, **stream_config
    )


def add_struct_loggers(config: LoggerConfig) -> None:
    '''
    Adds structured file loggers to the loguru logger instance.

    Parameters
    ----------
    config : LoggerConfig
        The logger configuration settings.
    '''
    file_options = {
        'rotation': f'{config.rotation_mb} MB',
        'retention': f'{config.retention_days} days',
        'compression': config.compression,
        'enqueue': True,
        'diagnose': False,
        'serialize': True,
    }

    security_no = logging.INFO + 5  # between info and warning

    def security_filter(record: Record, _no: int = security_no) -> bool:
        return record['level'].name == 'SECURITY' or record['level'].no == _no

    def error_filter(record: Record) -> bool:
        return record['level'].no >= logging.ERROR

    loguru_logger.add(
        _create_file_sink('security'),
        level=security_no,
        filter=security_filter,
        **file_options,
    )

    loguru_logger.add(
        _create_file_sink('errors'),
        level=logging.ERROR,
        filter=error_filter,
        **file_options,
    )


def initialize_logger(config: LoggerConfig) -> None:
    '''
    Configures the application logger based on the provided configuration.

    Parameters
    ----------
    config : LoggerConfig
        The logger configuration settings.
    '''
    loguru_logger.remove()
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    with contextlib.suppress(ValueError):
        loguru_logger.configure(
            patcher=_correlation_id_patch,
            levels=[
                {
                    'name': 'SECURITY',
                    'no': config.security_level_no,
                }
            ],
        )

    add_stream_loggers(config)
    add_struct_loggers(config)

    atexit.register(loguru_logger.complete)


def get_binded_loguru(**extras) -> Logger:
    '''
    Binds extra fields to the logger for structured logging.

    Parameters
    ----------
    **extras : dict
        Additional fields to bind to the logger.
    '''
    return loguru_logger.bind(**extras)


def get_logger() -> Logger:
    '''
    Returns the configured loguru logger instance.
    '''
    return loguru_logger
