"""
This module provides a simple log setup for the project. Supports on log with
multiple formats and file handlers. Note that we don't support log rotation yet.

Usage:
-----

References:
    1) https://stackoverflow.com/questions/11232230/logging-to-two-files-with-different-settings 

"""

import logging
import sys
import os.path
from datetime import datetime, date
from time import struct_time
from typing import TextIO

from src.static.static import DATETIME_PATTERN_FOR_FILENAME, DATE_PATTERN, DATETIME_PATTERN
from src.log.timezone import GetProgramTimezone


# ==================================================================================================
IS_DEFAULT_LOGGER_ENABLED: bool = False


# ==================================================================================================
def _BuildLogFilename(filename: str, rotate_enabled: bool, rotate_every_sec: bool) -> str:
    if rotate_enabled is False:
        return filename

    directory: str = os.path.dirname(filename)
    filename: str = os.path.basename(filename)
    extension: str = filename.split('.')[-1]
    filename = filename.removesuffix(f'.{extension}')

    if rotate_every_sec:
        dt: str = datetime.now(tz=GetProgramTimezone()).strftime(DATETIME_PATTERN_FOR_FILENAME)
    else:
        dt: str = date.today().strftime(DATE_PATTERN)

    log_filename = os.path.join(directory, f'{filename}_{dt}.{extension}')
    return log_filename


def _GetLogFormat(log_format: str) -> logging.Formatter:
    formatter = logging.Formatter(log_format)
    formatter.converter = _CustomTimeFormatter
    return formatter


def _CustomTimeFormatter(*args) -> struct_time:
    return datetime.now(tz=GetProgramTimezone()).timetuple()


def _BuildFileHandler(base_filename, filemode: str, rotate_log: bool, rotate_every_sec: bool,
                      encoding: str, delay: bool, errors: str | None,
                      log_format: str | None, handler_level=None) -> logging.FileHandler:
    # [00] Proceed with empty value:
    if log_format is None:
        log_format = r'[%(name)s-INFOFILE] [%(asctime)s] %(levelname)s: %(message)s'

    # [01] Build the log filename
    new_logfile = _BuildLogFilename(base_filename, rotate_log, rotate_every_sec)
    print(f"New logfile: {new_logfile}")
    if not os.path.exists(new_logfile):
        directory = os.path.dirname(new_logfile)
        if directory != '' and not os.path.exists(directory):
            # https://stackoverflow.com/questions/2967194/open-in-python-does-not-create-a-file-if-it-doesnt-exist
            # Credit to Chenglong Ma (Jan 30th, 2021) for the solution.
            os.makedirs(directory, exist_ok=True)
        open(new_logfile, 'x').close()

    # [02] Create the file handler
    file_handler = logging.FileHandler(new_logfile, mode=filemode, encoding=encoding, delay=delay,
                                       errors=errors if errors != "None" else None)
    if log_format is not None:
        file_handler.setFormatter(fmt=_GetLogFormat(log_format))
    if handler_level is not None:
        file_handler.setLevel(handler_level)
    return file_handler


def _BuildStreamHandler(stream: str | None, log_format: str | None, handler_level=None) -> logging.StreamHandler:
    stream_io: TextIO | None = None
    match stream:
        case 'ext://sys.stdout':
            stream_io = sys.stdout
        case 'ext://sys.stderr':
            stream_io = sys.stderr
        case _:
            pass

    stream_handler = logging.StreamHandler(stream=stream_io)
    if log_format is not None:
        stream_handler.setFormatter(_GetLogFormat(log_format))
    if handler_level is not None:
        stream_handler.setLevel(handler_level)
    return stream_handler


def _FullBuild(cfg: dict, handlers: list[logging.Handler] | None = None) -> list[logging.Handler]:
    if handlers is None:
        handlers: list[logging.Handler] = []

    for key, value in cfg.items():
        if 'FILE_HANDLER' in key:
            file_handler_enabled = value.get('ENABLED', False)
            if not file_handler_enabled:
                continue

            h = _BuildFileHandler(base_filename=value['LOG_FILE'], filemode=value['LOG_FILEMODE'],
                                  rotate_log=value['ROTATE_LOG'], rotate_every_sec=value['ROTATE_EVERY_SEC'],
                                  encoding=value['ENCODING'], delay=value['DELAY'], errors=value['ERRORS'],
                                  log_format=value['LOG_FORMAT'], handler_level=value['LEVEL'])
            handlers.append(h)

        if 'STREAM_HANDLER' in key:
            stream_handler_enabled = value.get('ENABLED', False)
            if not stream_handler_enabled:
                continue

            h = _BuildStreamHandler(stream=value['STREAM'], log_format=value['LOG_FORMAT'],
                                    handler_level=value['LEVEL'])
            handlers.append(h)

    return handlers

def presetDefaultLogging(cfg: dict) -> None:
    global IS_DEFAULT_LOGGER_ENABLED
    if IS_DEFAULT_LOGGER_ENABLED:
        return None

    logging.basicConfig(
        level=cfg['LEVEL'],
        datefmt=cfg.get('DATEFMT', DATETIME_PATTERN),
        handlers=_FullBuild(cfg, handlers=None),
        encoding=cfg.get('ENCODING', 'utf-8'),
        errors=cfg.get('ERRORS', None)
    )
    IS_DEFAULT_LOGGER_ENABLED = True
