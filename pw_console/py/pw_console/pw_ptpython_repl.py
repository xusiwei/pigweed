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
"""PwPtPythonPane class."""

import logging
from pathlib import Path

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from ptpython import repl  # type: ignore

_LOG = logging.getLogger(__package__)


class PwPtPythonRepl(repl.PythonRepl):
    """A ptpython repl based class with some overriden methods."""
    def __init__(self, *args, **kwargs):
        #self.ptpython_layout.show_status_bar = False
        #self.ptpython_layout.show_exit_confirmation = False
        super().__init__(*args,
                         history_filename=(Path.home() /
                                           ".pw_console_history").as_posix(),
                         color_depth="256 colors",
                         _input_buffer_height=8,
                         **kwargs)
        # self.use_code_colorscheme('monokai')
        self.use_code_colorscheme('zenburn')
        self.show_status_bar = False
        self.show_exit_confirmation = False
        self.complete_private_attributes = False
        self.repl_pane = None

    def __pt_container__(self):
        return self.ptpython_layout.root_container

    def set_repl_pane(self, repl_pane):
        self.repl_pane = repl_pane

    # pylint: disable=arguments-differ
    def show_result(self, result, print_to_stdout=True):
        # Format the result.
        formatted_result = super().show_result(result, print_to_stdout=False)  # pylint: disable=assignment-from-none,unexpected-keyword-arg
        # Throw away style info.
        unformatted_result = "".join(
            list(formatted_tuple[1] for formatted_tuple in formatted_result))  # pylint: disable=not-an-iterable

        # Get old buffer contents and append the result
        new_text = self.repl_pane.output_field.buffer.text
        new_text += unformatted_result

        # Set the output buffer to new_text and move the cursor to the end
        self.repl_pane.output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text))

    def _handle_exception(self, e: BaseException) -> None:
        # TODO: Display exception in output buffer.
        _LOG.debug(str(e))

    def _accept_handler(self, buff: Buffer) -> bool:
        # Do nothing if no text is entered.
        if len(buff.text) == 0:
            return False

        # Get old buffer contents
        new_text = self.repl_pane.output_field.buffer.text
        # Append the prompt and input
        new_text += "\n\n>>> " + buff.text + "\n"
        # Set the output buffer to new_text and move the cursor to the end
        self.repl_pane.output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text))

        # self._add_to_namespace()
        # try:
        self.run_and_show_expression(buff.text)
        # finally:
        #     self._remove_from_namespace()
        # TODO: Return True if exception is found.
        # Don't keep input for now. Return True to keep input text.
        return False
