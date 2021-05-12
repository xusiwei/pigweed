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
from typing import Any, List, Optional

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import (
    Condition,
    has_focus,
)
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    Float,
    FloatContainer,
    FormattedTextControl,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
    WindowAlign,
    UIContent,
    VerticalAlign,
)
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from pw_console.log_container import LogContainer

_LOG = logging.getLogger(__package__)


class LogPaneLineInfoBar(ConditionalContainer):
    """One line bar for showing current and total log lines."""
    @staticmethod
    def get_tokens(log_pane):
        """Return formatted text tokens for display."""
        tokens = ' Line {} / {} '.format(
            log_pane.log_container.get_current_line() + 1,
            log_pane.log_container.get_total_count(),
        )
        return [('', tokens)]

    def __init__(self, log_pane):
        info_bar_control = FormattedTextControl(
            partial(LogPaneLineInfoBar.get_tokens, log_pane))
        info_bar_window = Window(content=info_bar_control,
                                 align=WindowAlign.RIGHT,
                                 dont_extend_width=True)

        super().__init__(
            VSplit([info_bar_window],
                   height=1,
                   style='class:bottom_toolbar',
                   align=WindowAlign.RIGHT),
            # Hide line info if auto-following logs.
            filter=Condition(lambda: not log_pane.log_container.follow))


class LogPaneBottomToolbarBar(ConditionalContainer):
    """One line toolbar for display at the bottom of the LogPane."""
    @staticmethod
    def mouse_handler_focus(log_pane, mouse_event: MouseEvent):
        """Focus this pane on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            log_pane.application.application.layout.focus(log_pane)
            return None
        return NotImplemented

    @staticmethod
    def mouse_handler_toggle_wrap_lines(log_pane, mouse_event: MouseEvent):
        """Toggle wrap lines on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            log_pane.toggle_wrap_lines()
            return None
        return NotImplemented

    @staticmethod
    def mouse_handler_clear_history(log_pane, mouse_event: MouseEvent):
        """Clear history on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            log_pane.clear_history()
            return None
        return NotImplemented

    @staticmethod
    def mouse_handler_toggle_follow(log_pane, mouse_event: MouseEvent):
        """Toggle follow on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            log_pane.toggle_follow()
            return None
        return NotImplemented

    @staticmethod
    def get_center_text_tokens(log_pane):
        """Return formatted text tokens for display in the center part of the
        toolbar."""
        focus = partial(LogPaneBottomToolbarBar.mouse_handler_focus, log_pane)
        toggle_wrap_lines = partial(
            LogPaneBottomToolbarBar.mouse_handler_toggle_wrap_lines, log_pane)
        clear_history = partial(
            LogPaneBottomToolbarBar.mouse_handler_clear_history, log_pane)
        toggle_follow = partial(
            LogPaneBottomToolbarBar.mouse_handler_toggle_follow, log_pane)
        if has_focus(log_pane.__pt_container__())():
            return [
                ('', ' [FOCUSED]'),
                ('', ' '),
                ('class:keybind', 'w', toggle_wrap_lines),
                # TODO: Indicate wrap on/off
                ('class:keyhelp', ':Wrap', toggle_wrap_lines),
                ('', ' '),
                ('class:keybind', 'C', clear_history),
                ('class:keyhelp', ':Clear', clear_history),
                ('', ' '),
                ('class:keybind', 'f', toggle_follow),
                ('class:keyhelp', ':Follow', toggle_follow),
            ]
        return [
            ('class:keyhelp', ' [click to focus] ', focus),
        ]

    def __init__(self, log_pane):
        super().__init__(
            VSplit(
                [
                    Window(
                        content=FormattedTextControl(
                            # Logs [FOCUSED] w:Toggle wrap
                            [('class:logo', ' Logs ',
                              partial(
                                  LogPaneBottomToolbarBar.mouse_handler_focus,
                                  log_pane))]),
                        align=WindowAlign.LEFT,
                        dont_extend_width=True),
                    Window(content=FormattedTextControl(
                        partial(LogPaneBottomToolbarBar.get_center_text_tokens,
                                log_pane)),
                           align=WindowAlign.LEFT,
                           dont_extend_width=False),
                    # Window(content=FormattedTextControl(
                    #     [('class:bottom_toolbar_colored_text',
                    #       ' file_name=2021-03-05_1454_log.txt ',
                    #       partial(LogPaneBottomToolbarBar.mouse_handler,
                    #               log_pane))]),
                    #        align=WindowAlign.RIGHT,
                    #        dont_extend_width=True),
                ],
                height=1,
                style='class:bottom_toolbar',
                align=WindowAlign.LEFT),
            filter=Condition(lambda: log_pane.show_bottom_toolbar))


class LogContentControl(FormattedTextControl):
    """LogPane prompt_toolkit UIControl for displaying LogContainer lines."""
    @staticmethod
    def indent_wrapped_pw_log_format_line(log_pane, line_number, wrap_count):
        """Indent wrapped lines to match pw_cli timestamp & level formatter."""
        if wrap_count == 0:
            return None

        prefix = ' ' * log_pane.log_container.longest_channel_prefix_width

        # If this line matches the selected log line, highlight it.
        if line_number == log_pane.log_container.get_cursor_position().y:
            return to_formatted_text(prefix, style='class:selected-log-line')
        return prefix

    def create_content(self, width: int, height: Optional[int]) -> UIContent:
        # Save redered height
        if height:
            self.log_pane.last_log_content_height += height
        return super().create_content(width, height)

    def __init__(self, log_pane, *args, **kwargs):
        self.log_pane = log_pane

        # Key bindings.
        key_bindings = KeyBindings()

        @key_bindings.add('w')
        def _toggle_wrap_lines(_event: KeyPressEvent) -> None:
            """Toggle log line wrapping."""
            self.log_pane.toggle_wrap_lines()

        @key_bindings.add('C')
        def _clear_history(_event: KeyPressEvent) -> None:
            """Toggle log line wrapping."""
            self.log_pane.clear_history()

        @key_bindings.add('g')
        def _scroll_to_top(_event: KeyPressEvent) -> None:
            """Scroll to top."""
            self.log_pane.log_container.scroll_to_top()

        @key_bindings.add('G')
        def _scroll_to_bottom(_event: KeyPressEvent) -> None:
            """Scroll to bottom."""
            self.log_pane.log_container.scroll_to_bottom()

        @key_bindings.add('f')
        def _toggle_follow(_event: KeyPressEvent) -> None:
            """Toggle log line following."""
            self.log_pane.toggle_follow()

        @key_bindings.add('up')
        @key_bindings.add('k')
        def _up(_event: KeyPressEvent) -> None:
            """Select previous log line."""
            self.log_pane.log_container.scroll_up()

        @key_bindings.add('down')
        @key_bindings.add('j')
        def _down(_event: KeyPressEvent) -> None:
            """Select next log line."""
            self.log_pane.log_container.scroll_down()

        @key_bindings.add('pageup')
        def _pageup(_event: KeyPressEvent) -> None:
            """Scroll the logs up by one page."""
            self.log_pane.log_container.scroll_up_one_page()

        @key_bindings.add('pagedown')
        def _pagedown(_event: KeyPressEvent) -> None:
            """Scroll the logs down by one page."""
            self.log_pane.log_container.scroll_down_one_page()

        super().__init__(*args, key_bindings=key_bindings, **kwargs)

    def mouse_handler(self, mouse_event: MouseEvent):
        """Mouse handler for this control."""
        mouse_position = mouse_event.position

        # Check for pane focus first.
        # If not in focus, change forus to the log pane and do nothing else.
        if not has_focus(self)():
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                # Focus buffer when clicked.
                get_app().layout.focus(self)
                # Mouse event handled, return None.
                return None

        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            # Scroll to the line clicked.
            self.log_pane.log_container.scroll_to_position(mouse_position)
            # Mouse event handled, return None.
            return None

        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self.log_pane.log_container.scroll_down()
            # Mouse event handled, return None.
            return None

        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self.log_pane.log_container.scroll_up()
            # Mouse event handled, return None.
            return None

        # Mouse event not handled, return NotImplemented.
        return NotImplemented


class LogLineHSplit(HSplit):
    def __init__(self, log_pane, *args, **kwargs):
        self.log_pane = log_pane
        super().__init__(*args, **kwargs)

    def write_to_screen(
        self,
        screen,
        mouse_handlers,
        write_position,
        parent_style: str,
        erase_bg: bool,
        z_index: Optional[int],
    ) -> None:
        # Save current render pass width and height
        self.log_pane.update_log_pane_size(write_position.width,
                                           write_position.height)

        super().write_to_screen(screen, mouse_handlers, write_position,
                                parent_style, erase_bg, z_index)


@dataclass
class LogPane:
    """LogPane plugin class."""
    # pylint: disable=too-many-instance-attributes
    application: Any
    log_container: LogContainer = field(default_factory=LogContainer)
    show_bottom_toolbar = True
    show_line_info = True
    wrap_lines = True
    height = Dimension(weight=50)
    width = Dimension(weight=50)

    def __post_init__(self):
        """LogPane post initialize function, called after __init__()."""

        self.current_log_pane_width = 0
        self.current_log_pane_height = 0
        self.last_log_pane_width = 0
        self.last_log_pane_height = 0

        self._last_log_index = None
        self.last_log_content_height = 0

        # Set the passed in log_container instance's log_pane reference to this.
        self.log_container.set_log_pane(self)

        # Create the bottom toolbar for the whole log pane.
        self.bottom_toolbar = LogPaneBottomToolbarBar(self)
        self._last_selected_log_index = 0
        self._max_log_item_count = 10

        self.log_content_control = LogContentControl(
            self,  # parent LogPane
            # FormattedTextControl args:
            self.log_container.draw,
            # Hide the cursor, use cursorline=True in self.log_display_window to
            # indicate currently selected line.
            show_cursor=False,
            focusable=True,
            get_cursor_position=self.log_content_control_get_cursor_position,
        )

        self.log_display_window = Window(
            content=self.log_content_control,
            # TODO: ScrollOffsets here causes jumpiness when lines are wrapped.
            scroll_offsets=ScrollOffsets(top=0, bottom=0),
            allow_scroll_beyond_bottom=True,
            get_line_prefix=partial(
                LogContentControl.indent_wrapped_pw_log_format_line, self),
            wrap_lines=Condition(lambda: self.wrap_lines),
            cursorline=False,

            # Don't make the window taller to fill the parent split container.
            # Window should match the height of the log line content. This will
            # also allow the parent HSplit to justify the content to the bottom
            dont_extend_height=True,
            # Window width should be extended to make backround highlighting
            # extend to the end of the container. Otherwise backround colors
            # will only appear until the end of the log line.
            dont_extend_width=False,
        )

        # Root level container
        self.container = FloatContainer(
            LogLineHSplit(
                self,  # LogPane reference
                [
                    self.log_display_window,
                    self.bottom_toolbar,
                ],
                align=VerticalAlign.BOTTOM,
                height=self.height,
                width=self.width,
            ),
            floats=[
                Float(top=0,
                      right=0,
                      height=1,
                      content=LogPaneLineInfoBar(self)),
            ])

    def update_log_pane_size(self, width, height):
        if width:
            self.last_log_pane_width = self.current_log_pane_width
            self.current_log_pane_width = width
        if height:
            height -= 1  # Subtract 1 for the LogPaneBottomToolbarBar
            self.last_log_pane_height = self.current_log_pane_height
            self.current_log_pane_height = height

    def after_render_hook(self):
        self.reset_log_content_height()

    def reset_log_content_height(self):
        """Reset log line pane content height."""
        self.last_log_content_height = 0

    def is_in_focus(self):
        """Return if this LogPane is in focus or not."""
        console_app = self.application
        if not hasattr(console_app, 'application'):
            return False
        current_control = console_app.application.layout.current_window.content
        return current_control == self.log_content_control

    def redraw_ui(self):
        """Trigger a prompt_toolkit UI redraw."""
        self.application.redraw_ui()

    def log_content_control_get_cursor_position(self):
        return self.log_container.get_cursor_position()

    def toggle_wrap_lines(self):
        """Toggle line wraping/truncation."""
        self.wrap_lines = not self.wrap_lines
        self.redraw_ui()

    def toggle_follow(self):
        """Toggle following log lines."""
        self.log_container.toggle_follow()
        self.redraw_ui()

    def clear_history(self):
        """Erase stored log lines."""
        self.log_container.clear_logs()
        self.redraw_ui()

    def get_all_key_bindings(self) -> List:
        """Return all keybinds for this plugin."""
        # return [LogLineHSplit(self, []).get_key_bindings()]
        # return [LogContentControl(self).get_key_bindings()]
        return [self.log_content_control.get_key_bindings()]

    def __pt_container__(self):
        return self.container
