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
# pylint: skip-file
"""Console key bindings."""
import logging

from IPython.lib.pretty import pretty  # type: ignore

from prompt_toolkit.filters import (
    Condition,
    has_focus,
)
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.keys import Keys

# from prompt_toolkit.application import get_app
# from prompt_toolkit.filters import Condition, has_focus, vi_insert_mode, vi_navigation_mode

__all__ = ('create_key_bindings', )

_LOG = logging.getLogger(__package__)


def _current_window_for_event(event):
    """Return the `Window` for the currently focussed Buffer."""
    return event.app.layout.current_window


def create_key_bindings(console_app):
    """Create custom key bindings.

    This starts with the key bindings, defined by `prompt-toolkit`, but adds the
    ones which are specific for the console_app. A console_app instance
    reference is passed in so key bind functions can access it.
    """

    bindings = KeyBindings()

    @bindings.add("f1")
    def show_help(event):
        """Toggle help window."""
        _LOG.debug(pretty(event))
        console_app.toggle_help()

    @bindings.add("q", filter=Condition(lambda: console_app.show_help_window))
    def close_help_window(event):
        """Hide help window."""
        console_app.toggle_help()

    @bindings.add("c-c", filter=has_focus(console_app.pw_ptpython_repl))
    def handle_ctrl_c(event):
        """Reset the python repl on Ctrl-c"""
        console_app.pw_ptpython_repl.default_buffer.reset()

    @bindings.add("c-d", filter=has_focus(console_app.pw_ptpython_repl))
    def handle_ctrl_d(event):
        """Do nothing on ctrl-d."""
        pass

    @bindings.add("f2")
    def toggle_vertical_split(event):
        """Toggle horizontal and vertical window splitting."""
        _LOG.debug(pretty(event))
        console_app.toggle_vertical_split()

    @bindings.add("c-w")
    @bindings.add("c-q")
    def exit_(event):
        """Quit the console application."""
        event.app.exit()

    # Test calling the add decorator as function
    exit_ = bindings.add("c-e")(exit_)

    @bindings.add("s-tab")
    @bindings.add("c-right")
    @bindings.add("c-down")
    def app_focus_next(event):
        """Move focus to the next widget."""
        focus_next(event)

    @bindings.add("c-left")
    @bindings.add("c-up")
    def app_focus_previous(event):
        """Move focus to the previous widget."""
        focus_previous(event)

    return bindings
