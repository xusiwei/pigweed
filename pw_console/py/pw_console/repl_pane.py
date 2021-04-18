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
"""ReplPane class."""

import inspect
import logging
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

# from IPython.lib.pretty import pretty  # type: ignore
from prompt_toolkit.filters import (
    Condition,
    has_focus,
)
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.layout.dimension import AnyDimension
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    FormattedTextControl,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.lexers import PygmentsLexer  # type: ignore
from pygments.lexers.python import PythonLexer  # type: ignore

from pw_console.pw_ptpython_repl import PwPtPythonRepl

_LOG = logging.getLogger(__package__)

_Namespace = Dict[str, Any]
_GetNamespace = Callable[[], _Namespace]


class ReplPaneBottomToolbarBar(ConditionalContainer):
    """Repl pane bottom toolbar."""
    @staticmethod
    def mouse_handler(repl_pane, mouse_event: MouseEvent):
        """Focus this pane on click."""
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            repl_pane.application.application.layout.focus(repl_pane)
            return None
        return NotImplemented

    @staticmethod
    def get_center_text_tokens(repl_pane):
        """Return if the ReplPane is in focus or not."""
        if has_focus(repl_pane.__pt_container__())():
            return [
                ("", " [FOCUSED] ",
                 partial(ReplPaneBottomToolbarBar.mouse_handler, repl_pane)),
            ]
        return [
            # TODO: Clicking on the actual logs status bar doesn't focus; only
            # when clicking on the log content itself. Fix this.
            ("class:keyhelp", " [click to focus] ",
             partial(ReplPaneBottomToolbarBar.mouse_handler, repl_pane)),
        ]

    def __init__(self, repl_pane):
        super().__init__(
            VSplit(
                [
                    Window(content=FormattedTextControl(
                        [("class:logo", " Python Input ",
                          partial(ReplPaneBottomToolbarBar.mouse_handler,
                                  repl_pane))]),
                           align=WindowAlign.LEFT,
                           dont_extend_width=True),
                    Window(content=FormattedTextControl(
                        partial(
                            ReplPaneBottomToolbarBar.get_center_text_tokens,
                            repl_pane)),
                           align=WindowAlign.LEFT,
                           dont_extend_width=False),
                    Window(
                        content=FormattedTextControl(
                            [("class:bottom_toolbar_colored_text",
                              " [Enter]: run code ")]),
                        align=WindowAlign.RIGHT,
                        dont_extend_width=True),
                ],
                height=1,
                style="class:bottom_toolbar",
                align=WindowAlign.LEFT),
            filter=Condition(lambda: repl_pane.show_bottom_toolbar))


class ReplPane:
    """Pane for reading Python input."""

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
    def __init__(
            self,
            application: Any,
            python_repl: PwPtPythonRepl,
            # TODO: Make the height of input+output windows match the log pane
            # height. Use 5 for now.
            output_height: Optional[AnyDimension] = Dimension(preferred=15),
            unused_input_height: Optional[AnyDimension] = None) -> None:

        self.application = application
        self.show_top_toolbar = True
        self.show_bottom_toolbar = True

        self.pw_ptpython_repl = python_repl
        self.last_error_output = ""

        help_text = inspect.cleandoc("""
        Type any expression (e.g. "4 + 4") followed by enter to execute.
        """)

        if output_height:
            rows = 0
            if type(output_height).__name__ == 'int':
                rows = output_height  # type: ignore
            else:
                rows = output_height.min  # type: ignore
            help_text = ("\n" * rows) + help_text

        self.output_field = TextArea(
            style="class:output-field",
            height=output_height,
            # text=help_text,
            focusable=False,
            scrollbar=True,
            lexer=PygmentsLexer(PythonLexer),
        )
        self.pw_ptpython_repl.set_repl_pane(self)

        self.bottom_toolbar = ReplPaneBottomToolbarBar(self)

        self.container = HSplit([
            self.output_field,
            # Dashed line separator
            Window(content=FormattedTextControl([("class:logo",
                                                  " Python Results ")]),
                   height=1,
                   style="class:menu-bar"),
            self.pw_ptpython_repl,
            self.bottom_toolbar,
        ])

    def __pt_container__(self):
        """Return the prompt_toolkit container for this ReplPane."""
        return self.container

    # pylint: disable=no-self-use
    def get_all_key_bindings(self) -> List:
        """Return all keybinds for this plugin."""
        return []

    def append_to_output(self, formatted_text):
        pass
