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
"""LogPane plugin class."""

import logging
from dataclasses import dataclass, field
from functools import partial
from typing import Any, List

from IPython.lib.pretty import pretty  # type: ignore
from prompt_toolkit.application.current import get_app
# from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import (
    Condition,
    has_focus,
)
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    FormattedTextControl,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from pw_console.log_container import LogContainer

_LOG = logging.getLogger(__package__)


class LogPaneBottomToolbarBar(ConditionalContainer):
    """One line toolbar for display at the bottom of the LogPane."""
    @staticmethod
    def mouse_handler(log_pane, mouse_event: MouseEvent):
        """Focus this pane on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            log_pane.application.application.layout.focus(log_pane)
            return None
        return NotImplemented

    @staticmethod
    def get_center_text_tokens(log_pane):
        """Return formatted text tokens for display in the center part of the
        toolbar."""
        mouse_handler = partial(LogPaneBottomToolbarBar.mouse_handler,
                                log_pane)
        if has_focus(log_pane.__pt_container__())():
            return [
                ("", " [FOCUSED] ", mouse_handler),
                ("class:keybind", "w", mouse_handler),
                # TODO: Indicate wrap on/off
                ("class:keyhelp", ":Wrap ", mouse_handler),
            ]
        return [
            # TODO: Clicking on the actual logs status bar doesn't focus; only
            # when clicking on the log content itself. Fix this.
            ("class:keyhelp", " [click to focus] ", mouse_handler),
        ]

    def __init__(self, log_pane):
        super().__init__(
            VSplit(
                [
                    Window(
                        content=FormattedTextControl(
                            # Logs [FOCUSED] w:Toggle wrap
                            [("class:logo", " Logs ",
                              partial(LogPaneBottomToolbarBar.mouse_handler,
                                      log_pane))]),
                        align=WindowAlign.LEFT,
                        dont_extend_width=True),
                    Window(content=FormattedTextControl(
                        partial(LogPaneBottomToolbarBar.get_center_text_tokens,
                                log_pane)),
                           align=WindowAlign.LEFT,
                           dont_extend_width=False),
                    # Window(content=FormattedTextControl(
                    #     [("class:bottom_toolbar_colored_text",
                    #       " file_name=2021-03-05_1454_log.txt ",
                    #       partial(LogPaneBottomToolbarBar.mouse_handler,
                    #               log_pane))]),
                    #        align=WindowAlign.RIGHT,
                    #        dont_extend_width=True),
                ],
                height=1,
                style="class:bottom_toolbar",
                align=WindowAlign.LEFT),
            filter=Condition(lambda: log_pane.show_bottom_toolbar))


class LogContentControl(FormattedTextControl):
    """LogPane prompt_toolkit UIControl for displaying LogContainer lines."""
    @staticmethod
    def indent_wrapped_pw_log_format_line(unused_lineno, wrap_count):
        """Indent wrapped lines to match pw_cli timestamp & level formatter."""
        if wrap_count == 0:
            return None
        # Example
        # Log: '20210418 12:32:23 INF '
        return "                      "

    def __init__(self, log_pane, *args, **kwargs):
        self.log_pane = log_pane

        # Key bindings.
        key_bindings = KeyBindings()

        @key_bindings.add("w")
        def _toggle_wrap_lines(_event: KeyPressEvent) -> None:
            """Toggle log line wrapping."""
            self.log_pane.toggle_wrap_lines()

        @key_bindings.add("up")
        @key_bindings.add("k")
        def _up(event: KeyPressEvent) -> None:
            """Select next log line."""
            _LOG.debug(pretty(self) + " " + pretty(event))
            # self._selected_index = max(0, self._selected_index - 1)

        @key_bindings.add("down")
        @key_bindings.add("j")
        def _down(event: KeyPressEvent) -> None:
            """Select previous log line."""
            _LOG.debug(pretty(self) + " " + pretty(event))
            # self._selected_index = min(len(self.values) - 1,
            #                            self._selected_index + 1)

        @key_bindings.add("pageup")
        def _pageup(event: KeyPressEvent) -> None:
            """Scroll the logs up by one page."""
            _LOG.debug(pretty(self) + " " + pretty(event))
            # w = event.app.layout.current_window
            # if w.render_info:
            #     self._selected_index = max(
            #         0, self._selected_index - len(
            #             w.render_info.displayed_lines)
            #     )

        @key_bindings.add("pagedown")
        def _pagedown(event: KeyPressEvent) -> None:
            """Scroll the logs down by one page."""
            _LOG.debug(pretty(self) + " " + pretty(event))
            # w = event.app.layout.current_window
            # if w.render_info:
            #     self._selected_index = min(
            #         len(self.values) - 1,
            #         self._selected_index + len(w.render_info.displayed_lines),
            #     )

        super().__init__(*args, key_bindings=key_bindings, **kwargs)

    def mouse_handler(self, mouse_event: MouseEvent):
        """Mouse handler for this control."""
        mouse_position = mouse_event.position
        _LOG.debug(mouse_position)
        # Already in focus
        if get_app().layout.current_control == self:
            return NotImplemented
        # Focus buffer when clicked.
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            get_app().layout.current_control = self
        else:
            return NotImplemented
        return None


@dataclass
class LogPane:
    """LogPane plugin class."""
    # pylint: disable=too-many-instance-attributes
    application: Any
    log_container: LogContainer = field(default_factory=LogContainer)
    show_bottom_toolbar = True
    wrap_lines = True

    def __post_init__(self):
        """LogPane post initialize function, called after __init__()."""
        self.bottom_toolbar = LogPaneBottomToolbarBar(self)
        # Log Content control instnce
        self.log_content_control = LogContentControl(
            self,  # parent LogPane
            # FormattedTextControl args:
            self.log_container.draw,
            show_cursor=True,
            focusable=True,
        )
        self.log_container.set_log_content_control(self.log_content_control)

        self.log_display_window = Window(
            content=self.log_content_control,
            scroll_offsets=ScrollOffsets(bottom=1),
            get_line_prefix=LogContentControl.
            indent_wrapped_pw_log_format_line,
            wrap_lines=Condition(lambda: self.wrap_lines),
            # Make this window as tall as possible
            height=Dimension(preferred=10**10),
        )

        self.container = HSplit([
            self.log_display_window,
            self.bottom_toolbar,
        ])

    def toggle_wrap_lines(self):
        """Toggle line wraping/truncation."""
        self.wrap_lines = not self.wrap_lines

    def get_all_key_bindings(self) -> List:
        """Return all keybinds for this plugin."""
        return [self.log_content_control.get_key_bindings()]

    def __pt_container__(self):
        return self.container
