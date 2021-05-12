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
"""ConsoleApp control class."""

import argparse
import builtins
import asyncio
import logging
from threading import Thread
from typing import Iterable, Optional

from IPython.lib.pretty import pretty  # type: ignore
from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.styles import (
    Style,
    DynamicStyle,
    merge_styles,
)
from prompt_toolkit.layout import (
    ConditionalContainer,
    Float,
    FormattedTextControl,
    HSplit,
    Layout,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.widgets import FormattedTextToolbar
from prompt_toolkit.widgets import (
    MenuContainer,
    MenuItem,
)
from prompt_toolkit.key_binding import merge_key_bindings
from ptpython.key_bindings import load_python_bindings  # type: ignore

import pw_cli
from pw_console.help_window import HelpWindow
from pw_console.key_bindings import create_key_bindings
from pw_console.log_pane import LogPane
from pw_console.repl_pane import ReplPane
from pw_console.pw_ptpython_repl import PwPtPythonRepl

_LOG = logging.getLogger(__package__)
FAKE_DEVICE_LOGGER_NAME = 'fake_device.1'
_FAKE_DEVICE_LOG = logging.getLogger(FAKE_DEVICE_LOGGER_NAME)

BAR_STYLE = 'bg:#fdd1ff #432445'

pw_console_colors_base = {
    'bg-main': '#ffffff',
    'fg-main': '#000000',
    'bg-dim': '#f8f8f8',
    'fg-dim': '#282828',
    'bg-alt': '#f0f0f0',
    'fg-alt': '#505050',
} # yapf: disable

pw_console_styles = Style.from_dict({
    'top_toolbar_colored_background': 'bg:#c678dd #282c34',
    'top_toolbar': 'bg:#3e4452 #abb2bf',
    'top_toolbar_colored_text': 'bg:#282c34 #c678dd',

    'bottom_toolbar_colored_background': BAR_STYLE,
    'bottom_toolbar': BAR_STYLE,
    'bottom_toolbar_colored_text': BAR_STYLE,

    'frame.border': '',
    'shadow': 'bg:#282c34',
    'message': 'bg:#282c34 #c678dd',
    # 'scrollbar.arrow'
    # 'scrollbar.start'
    'scrollbar.background': 'bg:#3e4452 #abb2bf',
    'scrollbar.button': 'bg:#7f3285 #282c34',
    # 'scrollbar.end'

    'menu': 'bg:#3e4452 #bbc2cf',

    'menu-bar.selected-item': 'bg:#61afef #282c34',
    'menu-border': 'bg:#282c34 #61afef',

    'menu-bar': BAR_STYLE,

    # Top bar logo + critical shortcuts
    'logo':    BAR_STYLE + ' bold',
    'keybind': BAR_STYLE,
    'keyhelp': BAR_STYLE,

    'help_window_content': 'bg:default default',

    'cursor-line': 'bg:#3e4452 nounderline',
    'selected-log-line': 'bg:#3e4452',
}) # yapf: disable


def toolbar_mouse_handler(mouse_event):
    """Test toolbar mouse handler function."""
    _LOG.debug(pretty(mouse_event))
    # if mouse_event.event_type == MouseEventType.MOUSE_UP:
    return NotImplemented


def _create_top_toolbar() -> VSplit:
    """Create the global top toolbar."""
    return VSplit([
        Window(content=FormattedTextControl(
            [('class:top_toolbar_colored_background', ' LeftText ',
              toolbar_mouse_handler)]),
               align=WindowAlign.LEFT,
               dont_extend_width=True),
        Window(content=FormattedTextControl(
            [('class:top_toolbar', ' center text ')]),
               align=WindowAlign.LEFT,
               dont_extend_width=False),
        Window(content=FormattedTextControl(
            [('class:top_toolbar_colored_text', ' right-text ')]),
               align=WindowAlign.RIGHT,
               dont_extend_width=True),
    ],
                  height=1,
                  style='class:top_toolbar')


class MessageToolbarBar(ConditionalContainer):
    """Pop-up (at the bottom) for showing error/status messages."""
    def __init__(self, application):
        def get_tokens():
            if application.message:
                return application.message
            return []

        super().__init__(
            FormattedTextToolbar(get_tokens),
            filter=Condition(
                lambda: application.message and application.message != ''))


def embed(
    global_vars=None,
    local_vars=None,
    loggers: Optional[Iterable] = None,
    command_line_args: Optional[argparse.Namespace] = None,
    test_mode=False,
) -> None:
    console_app = ConsoleApp(
        global_vars=global_vars,
        local_vars=local_vars,
    )

    if loggers:
        for logger in loggers:
            console_app.add_log_handler(logger)

    if command_line_args:
        _LOG.debug(pretty(command_line_args))

    # Start a thread for running user code.
    console_app.start_user_code_thread()
    # Start the prompt toolkit app
    asyncio.run(console_app.run(test_mode=test_mode), debug=True)


class ConsoleApp:
    # pylint: disable=too-many-instance-attributes
    """The main ConsoleApp class containing the whole console."""
    def __init__(self, global_vars=None, local_vars=None):

        # Default global_vars/locals
        if global_vars is None:
            global_vars = {
                '__name__': '__main__',
                '__package__': None,
                '__doc__': None,
                '__builtins__': builtins,
            }

        local_vars = local_vars or global_vars

        self.user_code_loop = asyncio.new_event_loop()

        self.message = [
            ('class:logo', ' Pigweed CLI v0.1 '),
            ('class:menu-bar', '| Mouse supported; click on pane to focus | '),
            ('class:keybind', 'F1'),
            ('class:keyhelp', ':Help '),
            ('class:keybind', 'Ctrl-W'),
            ('class:keyhelp', ':Quit '),
        ]
        # 'Pigweed CLI v0.1 | Mouse supported | F1:Help F7:Quit.'
        self.show_help_window = False
        self.vertical_split = False

        self.log_pane = LogPane(application=self)

        # Setup log_pane formatting
        # Copy of pw_cli log formatter
        colors = pw_cli.color.colors(True)
        timestamp_fmt = colors.black_on_white('%(asctime)s') + ' '
        formatter = logging.Formatter(
            timestamp_fmt + '%(levelname)s %(message)s', '%Y%m%d %H:%M:%S')

        self.log_pane.log_container.setLevel(logging.DEBUG)
        self.log_pane.log_container.setFormatter(formatter)

        self.pw_ptpython_repl = PwPtPythonRepl(
            get_globals=lambda: global_vars,
            get_locals=lambda: local_vars,
        )

        self.repl_pane = ReplPane(
            application=self,
            python_repl=self.pw_ptpython_repl,
        )

        self.active_panes = [
            self.log_pane,
            self.repl_pane,
        ]

        self.menu_items = [
            MenuItem(
                '[File] ',
                children=[
                    MenuItem('Exit', handler=self.exit_console),
                ],
            ),
            MenuItem(
                '[View] ',
                children=[
                    MenuItem('Toggle Vertical/Horizontal Split',
                             handler=self.toggle_vertical_split),
                    MenuItem('Toggle Log line Wrapping',
                             handler=self.toggle_log_line_wrapping),
                ],
            ),
            MenuItem(
                '[Info] ',
                children=[MenuItem('Help', handler=self.toggle_help)],
            ),
        ]

        # Key bindings registry.
        self.key_bindings = create_key_bindings(self)

        self.root_container = MenuContainer(
            body=self._create_root_split(),
            menu_items=self.menu_items,
            floats=[
                # Message Echo Area
                Float(top=0,
                      right=0,
                      height=1,
                      content=MessageToolbarBar(self)),
                # Centered floating Help Window
                Float(content=self._create_help_window()
                      # right=2, top=2,
                      ),
                # TODO: Figure out how to use this completion menu instead of
                # the one built into ptpython.
                # Completion menu that can overlap other panes.
                # Float(
                #     xcursor=True,
                #     ycursor=True,
                #     content=CompletionsMenu(max_height=16, scroll_offset=1),
                # ),
            ],
        )

        self.layout: Layout = Layout(self.root_container,
                                     focused_element=self.repl_pane)

        self.application: Application = Application(
            layout=self.layout,
            after_render=self.run_after_render_hooks,
            key_bindings=merge_key_bindings([
                load_python_bindings(self.pw_ptpython_repl),
                self.key_bindings,
            ]),
            style=DynamicStyle(lambda: merge_styles(
                [pw_console_styles, self.pw_ptpython_repl._current_style])),  # pylint: disable=protected-access
            enable_page_navigation_bindings=True,
            full_screen=True,
            mouse_support=True)

    def _user_code_thread_entry(self):
        """Entry point for the user code thread."""
        asyncio.set_event_loop(self.user_code_loop)
        self.user_code_loop.run_forever()

    def run_after_render_hooks(self, *unused_args, **unused_kwargs):
        # Don't query the terminal size after every render, it's very
        # slow. Better to let prompt_toolkit handle this and instead save
        # container sizes at render time.
        # self.size = self.application.renderer.output.get_size()

        # Run each active pane's after_render_hook if defined.
        for pane in self.active_panes:
            if hasattr(pane, 'after_render_hook'):
                pane.after_render_hook()

    def start_user_code_thread(self):
        """Create a thread for running user code so the UI isn't blocked."""
        thread = Thread(target=self._user_code_thread_entry,
                        args=(),
                        daemon=True)
        thread.start()

    def add_log_handler(self, logger_instance):
        # Don't send to globabl logging
        # logger_instance.propagate = False
        logger_instance.addHandler(self.log_pane.log_container)

    def _create_help_window(self):
        help_window = HelpWindow(self)
        # Create the help window and generate help text.
        # Add global key bindings to the help text
        help_window.add_keybind_help_text('Global', self.key_bindings)
        # Add activated plugin key bindings to the help text
        for pane in self.active_panes:
            for key_bindings in pane.get_all_key_bindings():
                help_window.add_keybind_help_text(pane.__class__.__name__,
                                                  key_bindings)
        help_window.generate_help_text()
        return help_window

    def _create_root_split(self):
        if self.vertical_split:
            self.active_pane_split = VSplit(
                self.active_panes,
                # Add a vertical separator between each active window pane.
                padding=1,
                padding_char='│',
                padding_style='',
            )
        else:
            self.active_pane_split = HSplit(self.active_panes)

        return HSplit([
            self.active_pane_split,
        ])

    def toggle_log_line_wrapping(self):
        """Menu item handler to toggle line wrapping of the first log pane."""
        self.log_pane.toggle_wrap_lines()

    def toggle_vertical_split(self):
        """Toggle visibility of the help window."""
        self.vertical_split = not self.vertical_split
        # For a root FloatContainer
        # self.root_container.content = self._create_root_split()
        # For a root MenuContainer
        self.root_container.container.content.children[
            1] = self._create_root_split()
        self.redraw_ui()

    def toggle_help(self):
        """Toggle visibility of the help window."""
        self.show_help_window = not self.show_help_window

    def exit_console(self):
        """Quit the console prompt_toolkit application UI."""
        self.application.exit()

    def redraw_ui(self):
        """Redraw the prompt_toolkit UI."""
        self.application.invalidate()

    async def run(self, test_mode=False):
        """Start the prompt_toolkit UI."""
        if test_mode:
            background_log_task = asyncio.create_task(self.log_forever())

        try:
            unused_result = await self.application.run_async(
                set_exception_handler=True)
            # Application.run_async() is similar to:
            # asyncio.get_event_loop().run_until_complete()
            # Params:
            # pre_run: Optional callable, which is called right after the
            #          "reset" of the application.
            # set_exception_handler: When set, in case of an exception, go
            #                        out of the alternate screen and hide
            #                        the application, display the exception,
            #                        and wait for the user to press ENTER.
        finally:
            if test_mode:
                background_log_task.cancel()

    async def log_forever(self):
        """Test mode async log generator coroutine that runs forever."""
        message_count = 0
        # Sample log lines:
        # Log message [=         ] # 291
        # Log message [ =        ] # 292
        # Log message [  =       ] # 293
        # Log message [   =      ] # 294
        # Log message [    =     ] # 295
        # Log message [     =    ] # 296
        # Log message [      =   ] # 297
        # Log message [       =  ] # 298
        # Log message [        = ] # 299
        # Log message [         =] # 300
        while True:
            await asyncio.sleep(2)
            bar_size = 10
            position = message_count % bar_size
            bar_content = " " * (bar_size - position - 1) + "="
            if position > 0:
                bar_content = "=".rjust(position) + " " * (bar_size - position)
            new_log_line = 'Log message [{}] # {}'.format(
                bar_content, message_count)
            if message_count % 10 == 0:
                new_log_line += (" Lorem ipsum dolor sit amet, consectetur "
                                 "adipiscing elit.") * 8
            # Create a log line with linebreaks
            # if message_count % 11 == 0:
            #     new_log_line += inspect.cleandoc(""" [PYTHON] START
            #         In []: import time;
            #                 def t(s):
            #                     time.sleep(s)
            #                     return 't({}) seconds done'.format(s)""")

            message_count += 1
            _FAKE_DEVICE_LOG.info(new_log_line)

    @property
    def add_key_binding(self):
        """Shortcut for adding new key bindings.

        Useful for an rc file that receives this ConsoleApp instance as input.
        """
        return self.key_bindings.add
