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
import concurrent
import logging
from dataclasses import dataclass
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

# from IPython.lib.pretty import pretty  # type: ignore
from jinja2 import Template
from prompt_toolkit.filters import (
    Condition,
    has_focus,
)
from prompt_toolkit.document import Document
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.layout.dimension import AnyDimension
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    Float,
    FloatContainer,
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


def mouse_focus_handler(repl_pane, mouse_event: MouseEvent):
    """Focus the repl_pane on click."""
    if not has_focus(repl_pane)():
        if mouse_event.event_type == MouseEventType.MOUSE_UP:
            repl_pane.application.application.layout.focus(repl_pane)
            return None
        # If any actions should happen if in focus NotImplemented should be
        # returned here.
        # return NotImplemented
    return NotImplemented


class FocusOnClickFloatContainer(ConditionalContainer):
    """Empty container shown if the repl_pane is not in focus.

    Container is hidden if already in focus.
    """
    def __init__(self, repl_pane):
        super().__init__(Window(
            FormattedTextControl([('', ' ',
                                   partial(mouse_focus_handler,
                                           repl_pane))]), ),
                         filter=Condition(lambda: not has_focus(repl_pane)()))


class ReplPaneBottomToolbarBar(ConditionalContainer):
    """Repl pane bottom toolbar."""
    @staticmethod
    def get_center_text_tokens(repl_pane):
        """Return if the ReplPane is in focus or not."""
        if has_focus(repl_pane)():
            return [
                ("", " [FOCUSED] ", partial(mouse_focus_handler, repl_pane)),
            ]
        return [
            ('class:keyhelp', ' [click to focus] ',
             partial(mouse_focus_handler, repl_pane)),
        ]

    def __init__(self, repl_pane):
        super().__init__(
            VSplit(
                [
                    Window(content=FormattedTextControl(
                        [('class:logo', ' Python Input ',
                          partial(mouse_focus_handler, repl_pane))]),
                           align=WindowAlign.LEFT,
                           dont_extend_width=True),
                    Window(content=FormattedTextControl(
                        partial(
                            ReplPaneBottomToolbarBar.get_center_text_tokens,
                            repl_pane)),
                           align=WindowAlign.LEFT,
                           dont_extend_width=False),
                    Window(content=FormattedTextControl(
                        [('class:bottom_toolbar_colored_text',
                          ' [Enter]: run code ')]),
                           align=WindowAlign.RIGHT,
                           dont_extend_width=True),
                ],
                height=1,
                style='class:bottom_toolbar',
                align=WindowAlign.LEFT),
            filter=Condition(lambda: repl_pane.show_bottom_toolbar))


@dataclass
class UserCodeExecution:
    """Class to hold a single user repl execution."""
    input: str
    future: concurrent.futures.Future
    output: str
    stdout: str
    stderr: str

    @property
    def is_running(self):
        return not self.future.done()


class ReplPane:
    """Pane for reading Python input."""

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
    def __init__(
            self,
            application: Any,
            python_repl: PwPtPythonRepl,
            # TODO: Make the height of input+output windows match the log pane
            # height. Use 15 for now.
            output_height: Optional[AnyDimension] = Dimension(preferred=5),
            unused_input_height: Optional[AnyDimension] = None,
            height: Optional[AnyDimension] = Dimension(weight=50),
            width: Optional[AnyDimension] = Dimension(weight=50),
    ) -> None:
        self.height = height
        self.width = width

        self.executed_code: List = []
        self.application = application
        self.show_top_toolbar = True
        self.show_bottom_toolbar = True

        self.pw_ptpython_repl = python_repl
        self.last_error_output = ""

        self.output_field = TextArea(
            style='class:output-field',
            height=output_height,
            # text=help_text,
            focusable=False,
            scrollbar=True,
            lexer=PygmentsLexer(PythonLexer),
        )
        self.pw_ptpython_repl.set_repl_pane(self)

        self.bottom_toolbar = ReplPaneBottomToolbarBar(self)

        self.container = FloatContainer(
            HSplit(
                [
                    self.output_field,
                    # Dashed line separator
                    Window(content=FormattedTextControl(
                        [('class:logo', ' Python Results ')]),
                           height=1,
                           style='class:menu-bar'),
                    self.pw_ptpython_repl,
                    self.bottom_toolbar,
                ],
                height=self.height,
                width=self.width,
            ),
            floats=[
                # Transparent float container that will focus on the repl_pane
                # when clicked. It is hidden if already in focus.
                Float(
                    FocusOnClickFloatContainer(self),
                    transparent=True,
                    right=0,
                    left=0,
                    top=0,
                    bottom=1,
                ),
            ])

    def __pt_container__(self):
        """Return the prompt_toolkit container for this ReplPane."""
        return self.container

    # pylint: disable=no-self-use
    def get_all_key_bindings(self) -> List:
        """Return all keybinds for this plugin."""
        return []

    def ctrl_c(self):
        """Ctrl-C keybinding behavior."""
        # If there is text in the input buffer, clear it.
        if self.pw_ptpython_repl.default_buffer.text:
            self.clear_input_buffer()
        else:
            self.interrupt_last_code_execution()

    def clear_input_buffer(self):
        self.pw_ptpython_repl.default_buffer.reset()

    def interrupt_last_code_execution(self):
        code = self._get_currently_running_code()
        if code:
            code.future.cancel()
            code.output = 'Canceled'
        self.pw_ptpython_repl.clear_last_result()
        self.update_output_buffer()

    def _get_currently_running_code(self):
        for code in self.executed_code:
            if not code.future.done():
                return code
        return None

    def _get_executed_code(self, future):
        for code in self.executed_code:
            if code.future == future:
                return code
        return None

    def _log_executed_code(self, code, prefix=''):
        text = self.get_output_buffer_text([code], show_index=False)
        _LOG.info('[PYTHON] %s\n%s', prefix, text)

    def append_executed_code(self, text, future):
        user_code = UserCodeExecution(input=text,
                                      future=future,
                                      output=None,
                                      stdout=None,
                                      stderr=None)
        self.executed_code.append(user_code)
        self._log_executed_code(user_code, prefix='START')

    def append_result_to_executed_code(self,
                                       _input_text,
                                       future,
                                       result_text,
                                       stdout_text='',
                                       stderr_text=''):
        code = self._get_executed_code(future)
        if code:
            code.output = result_text
            code.stdout = stdout_text
            code.stderr = stderr_text
        self._log_executed_code(code, prefix='FINISH')
        self.update_output_buffer()

    def get_output_buffer_text(self, code_items=None, show_index=True):
        executed_code = code_items or self.executed_code
        template_text = inspect.cleandoc("""
            {% for code in code_items %}
            {% set index = loop.index if show_index else '' %}
            {% set prompt_width = 7 + index|string|length %}
            In [{{index}}]: {{ code.input|indent(width=prompt_width) }}
            {% if code.is_running %}
            Running...
            {% else %}
            {% if code.stdout -%}
              {{ code.stdout }}
            {%- endif %}
            {% if code.stderr -%}
              {{ code.stderr }}
            {%- endif %}
            {% if code.output %}
            Out[{{index}}]: {{ code.output|indent(width=prompt_width) }}
            {% endif %}
            {% endif %}

            {% endfor %}
            """)
        template = Template(template_text,
                            trim_blocks=True,
                            lstrip_blocks=True)
        return template.render(code_items=executed_code,
                               show_index=show_index).strip()

    def update_output_buffer(self):
        text = self.get_output_buffer_text()
        self.output_field.buffer.document = Document(text=text,
                                                     cursor_position=len(text))
        self.application.redraw_ui()
