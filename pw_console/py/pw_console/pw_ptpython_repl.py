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

import asyncio
import logging
import io
import sys
from functools import partial
from pathlib import Path

from prompt_toolkit.buffer import Buffer
from ptpython import repl  # type: ignore

from pw_console.utils import remove_formatting

_LOG = logging.getLogger(__package__)


class PwPtPythonRepl(repl.PythonRepl):
    """A ptpython repl based class with some overriden methods."""
    def __init__(self, *args, **kwargs):
        #self.ptpython_layout.show_status_bar = False
        #self.ptpython_layout.show_exit_confirmation = False
        super().__init__(*args,
                         create_app=False,
                         history_filename=(Path.home() /
                                           '.pw_console_history').as_posix(),
                         color_depth='256 colors',
                         _input_buffer_height=8,
                         **kwargs)
        # self.use_code_colorscheme('monokai')
        self.use_code_colorscheme('zenburn')
        self.show_status_bar = False
        self.show_exit_confirmation = False
        self.complete_private_attributes = False
        self.repl_pane = None
        self._last_result = None

    def __pt_container__(self):
        return self.ptpython_layout.root_container

    def set_repl_pane(self, repl_pane):
        self.repl_pane = repl_pane

    def _save_result(self, formatted_text):
        """Save the last repl execution result."""
        # TODO: This isn't thread safe.
        unformatted_result = remove_formatting(formatted_text)
        # Save last result
        self._last_result = unformatted_result

    def clear_last_result(self):
        """Erase the last repl execution result."""
        self._last_result = None

    def _update_output_buffer(self):
        self.repl_pane.update_output_buffer()

    def show_result(self, result):
        formatted_result = self._format_result_output(result)
        self._save_result(formatted_result)

    def _handle_exception(self, e: BaseException) -> None:
        formatted_result = self._format_exception_output(e)
        self._save_result(formatted_result.__pt_formatted_text__())

    def user_code_complete_callback(self, input_text, future):
        """Callback to run after user repl code is finished."""
        # If there was an exception it will be saved in self._last_result
        result = self._last_result
        # _last_result consumed, erase for the next run.
        self.clear_last_result()

        stdout_contents = None
        stderr_contents = None
        if future.result():
            future_result = future.result()
            stdout_contents = future_result['stdout']
            stderr_contents = future_result['stderr']
            result_value = future_result['result']

            if result_value is not None:
                formatted_result = self._format_result_output(result_value)
                result = remove_formatting(formatted_result)

        # Job is finished, append the last result.
        self.repl_pane.append_result_to_executed_code(input_text, future,
                                                      result, stdout_contents,
                                                      stderr_contents)

        # Rebuild output buffer.
        self._update_output_buffer()

        # Trigger a prompt_toolkit application redraw.
        self.repl_pane.application.application.invalidate()

    async def _run_user_code(self, text):
        """Run user code and capture stdout+err."""

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        temp_out = io.StringIO()
        temp_err = io.StringIO()

        sys.stdout = temp_out
        sys.stderr = temp_err

        try:
            result = await self.run_and_show_expression_async(text)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        stdout_contents = temp_out.getvalue()
        stderr_contents = temp_err.getvalue()

        return {
            'stdout': stdout_contents,
            'stderr': stderr_contents,
            'result': result
        }

    def _accept_handler(self, buff: Buffer) -> bool:
        # Do nothing if no text is entered.
        if len(buff.text) == 0:
            return False

        # Execute the repl code in the user_code thread loop
        future = asyncio.run_coroutine_threadsafe(
            self._run_user_code(buff.text),
            self.repl_pane.application.user_code_loop)
        # Run user_code_complete_callback() when done.
        done_callback = partial(self.user_code_complete_callback, buff.text)
        future.add_done_callback(done_callback)

        # Save the input text and future.
        self.repl_pane.append_executed_code(buff.text, future)

        # Rebuild output buffer.
        self._update_output_buffer()

        # TODO: Return True if exception is found.
        # Don't keep input for now. Return True to keep input text.
        return False
