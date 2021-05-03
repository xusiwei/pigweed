# Copyright 2020 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Pigweed console main entry point."""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pw_cli.log
from pw_tokenizer.database import LoadTokenDatabases

from pw_console.console_app import embed, FAKE_DEVICE_LOGGER_NAME

_LOG = logging.getLogger(__package__)


def build_argument_parser() -> argparse.ArgumentParser:
    """Setup argparse."""
    def log_level(arg: str) -> int:
        try:
            return getattr(logging, arg.upper())
        except AttributeError as err:
            raise argparse.ArgumentTypeError(
                f"{arg.upper()} is not a valid log level") from err

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-l",
                        "--loglevel",
                        type=log_level,
                        default=logging.INFO,
                        help="Set the log level "
                        "(debug, info, warning, error, critical)")
    parser.add_argument("--logfile", help="Pigweed Console debug log file.")

    pw_root_path = Path(
        os.environ.get('PW_ROOT',
                       Path(__file__).parent.parent.parent.parent))
    config_file_name = '.pw_console.conf'
    config_file_path = pw_root_path / config_file_name
    parser.add_argument("-c",
                        "--config-file",
                        default=config_file_path.as_posix(),
                        help="File to write device logs. "
                        f"Default: {config_file_path.as_posix()}")

    parser.add_argument("--tokenizer-databases",
                        metavar='elf_or_token_database',
                        nargs="+",
                        action=LoadTokenDatabases,
                        help="Path to tokenizer database csv file(s).")

    parser.add_argument("--test-mode",
                        action="store_true",
                        help="Enable fake log messages for testing purposes.")

    log_default_filename = datetime.now().strftime(
        "%Y-%m-%d_%H%M") + "_log.txt"
    parser.add_argument("--device-logfile",
                        default=log_default_filename,
                        help="File to write device logs. "
                        f"Default: {log_default_filename}")

    parser.add_argument('terminal_args',
                        nargs=argparse.REMAINDER,
                        help='Arguments to forward to the terminal widget.')

    return parser


def main() -> int:
    """Pigweed Console."""

    parser = build_argument_parser()
    args, unused_extra_args = parser.parse_known_args()

    if "--" in args.terminal_args:
        args.terminal_args.remove("--")

    pw_cli.log.install(args.loglevel, True, False, args.logfile)

    default_loggers = []
    if args.test_mode:
        default_loggers = [_LOG, logging.getLogger(FAKE_DEVICE_LOGGER_NAME)]

    embed(loggers=default_loggers,
          command_line_args=args,
          test_mode=args.test_mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
