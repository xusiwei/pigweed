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
"""Help window container class."""

import logging
import inspect
from functools import partial

from jinja2 import Template
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout import (
    ConditionalContainer,
    FormattedTextControl,
    Window,
)
from prompt_toolkit.widgets import (Box, Frame)

_LOG = logging.getLogger(__package__)


class HelpWindow(ConditionalContainer):
    """Help window container for displaying keybindings."""
    def get_tokens(self, application):
        """Get text for the help window FormattedTextControl."""
        if application.show_help_window:
            return [('class:help_window_content', self.help_text)]
        return []

    def __init__(self, application):
        self.help_text_section = {}
        self.max_description_width = 0
        self.help_text = ''

        super().__init__(
            Frame(body=Box(
                body=Window(
                    FormattedTextControl(partial(self.get_tokens,
                                                 application)),
                    style='class:help_window_content',
                ),
                padding=1,
                char=' ',
            ), ),
            filter=Condition(lambda: application.show_help_window))

    def generate_help_text(self):
        """Geneate help text based on added key_bindings."""

        # pylint: disable=line-too-long
        template_text = inspect.cleandoc("""
            {% for section, key_dict in sections.items() %}
            {{ section|center }}

            {% for description, key_list in key_dict.items() %}
            {{ (description+' ').ljust(max_description_width+3, '-') }}  {{ key_list|sort|join(', ') }}
            {% endfor %}

            {% endfor %}
            """)
        template = Template(
            template_text,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.help_text = template.render(
            sections=self.help_text_section,
            max_description_width=self.max_description_width)
        return self.help_text

    def add_keybind_help_text(self, section_name, key_bindings):
        """Append formatted key binding text to this help window."""

        if section_name not in self.help_text_section:
            self.help_text_section[section_name] = {}

        for binding in key_bindings.bindings:
            description = inspect.cleandoc(binding.handler.__doc__)
            if len(description) > self.max_description_width:
                self.max_description_width = len(description)

            keylist = self.help_text_section[section_name].get(
                description, list())
            key_name = getattr(binding.keys[0], 'name', str(binding.keys[0]))
            keylist.append(key_name)
            self.help_text_section[section_name][description] = keylist
