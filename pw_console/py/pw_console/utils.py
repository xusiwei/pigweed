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
"""Helper utility functions."""


def human_readable_size(size, decimal_places=2):
    """Return bytes as a string in human readable form."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f'{size:.{decimal_places}f} {unit}'


def remove_formatting(formatted_text):
    """Throw away style info from formatted text tuples."""
    return ''.join([formatted_tuple[1] for formatted_tuple in formatted_text])  # pylint: disable=not-an-iterable


def formatted_text_splitlines(formatted_text_tuples):
    lines = [[]]
    for index, fragment in enumerate(formatted_text_tuples):
        # if len(lines[-1]) > 0 and lines[-1][-1][0] == fragment[0]:
        #     lines[-1][-1] = (fragment[0], lines[-1][-1][1] + fragment[1])
        # else:
        lines[-1].append(fragment)
        if fragment[1] == '\n' and index < len(formatted_text_tuples) - 1:
            lines.append([])
    return lines


def get_line_height(text_width, screen_width, prefix_width):
    if text_width == 0:
        return 0
    if text_width < screen_width:
        return 1

    total_height = 1
    remaining_width = text_width - screen_width

    while (remaining_width + prefix_width) > screen_width:
        remaining_width += prefix_width
        remaining_width -= screen_width
        total_height += 1

    # Add one for the last line that is < screen_width
    return total_height + 1
