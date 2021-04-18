# Copyright 2021 The Pigweed Authors
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
"""LogLine and LogContainer."""

import logging
import sys

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

from prompt_toolkit.formatted_text import ANSI

from pw_console.utils import human_readable_size

_LOG = logging.getLogger(__package__)


@dataclass
class LogLine:
    """Class to hold a single log event."""
    record: logging.LogRecord
    formatted_log: str

    def time(self):
        """Return a datetime object for the log record."""
        return datetime.fromtimestamp(self.record.created)

    def get_fragments(self) -> List:
        """Return this log line as a list of FormattedText tuples."""
        # Manually make a FormattedText tuple, wrap in a list
        # return [("class:bottom_toolbar_colored_text", self.record.msg + '\n')]
        # Use ANSI, returns a list of tuples
        return ANSI(self.formatted_log + '\n').__pt_formatted_text__()


class LogContainer(logging.Handler):
    """Class to hold many log events."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.logs: deque = deque()
        self.byte_size: int = 0
        self.history_size: int = 1000
        self.channel_counts: Dict = {}
        self.line_index = 0
        self.follow = True
        self.log_content_control = None
        self.pt_application = None

        super().__init__()

    def get_total_count(self):
        """Total size of the logs container."""
        return len(self.logs)

    def get_channel_counts(self):
        """Return the seen channel log counts for the conatiner."""
        return ", ".join([
            f"{name}: {count}" for name, count in self.channel_counts.items()
        ])

    def get_human_byte_size(self):
        """Estimate the size of logs in memory."""
        return human_readable_size(self.byte_size)

    def _append_log(self, record):
        """Add a new log event."""
        self.logs.append(
            LogLine(record=record, formatted_log=self.format(record)))
        self.channel_counts[record.name] = self.channel_counts.get(
            record.name, 0) + 1

        self.byte_size += sys.getsizeof(self.logs[-1])
        if len(self.logs) > self.history_size:
            self.byte_size -= sys.getsizeof(self.logs.popleft())

        if self.follow:
            self.line_index = max(0, len(self.logs) - 1)

    # logging.Handler emit() fuction. This is called by logging.Handler.handle()
    # We don't implement handle() as it is done parent class with thread safety
    # and filters applied.
    def emit(self, record):
        """Process log record."""
        self._append_log(record)
        console_app = self.log_content_control.log_pane.application
        if hasattr(console_app, 'application'):
            console_app.application.invalidate()

    def draw(self) -> List:
        """Return this log line as a FormattedTextControl."""
        starting_index = 0
        ending_index = self.line_index

        current_window_height = self.get_log_content_window_height()
        if current_window_height > 0:
            starting_index = max(0, self.line_index - current_window_height)
            # Note: Line wrapping isn't taken into account for the visible log
            # range when calculating starting_index and ending_index.

        fragments = []
        for i in range(starting_index, ending_index):
            for fragment in self.logs[i].get_fragments():
                fragments.append(fragment)
        return fragments

    def get_log_content_window_height(self) -> int:
        """Get the height of the log window."""
        # Get height of the parent LogPane from the last time prompt_toolkit
        # rendered the content.
        log_window = self.log_content_control.log_pane.log_display_window
        if log_window.render_info:
            return log_window.render_info.window_height
        return 0

    def set_log_content_control(self, log_content_control):
        """Set the parent LogContentControll instance."""
        self.log_content_control = log_content_control
