"""
MIT License

Copyright (c) 2025 Sébastien Gachoud

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

-------------------------------------------------------------------------------

Author: Sébastien Gachoud
Created: 2025-07-11
Description: Base class and functions to ease exception tracing in a string.
🦙
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"


import traceback


def format_exception(e: Exception) -> str:
    """Format the provided exception to a string with its traceback.

    Args:
        e (Exception): The exception to format.

    Returns:
        str: The string representation of the exception with its traceback.
    """
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


class TracedException(Exception):
    """Base traceable exception class."""

    def traceback_format(self) -> str:
        """Format the exception to a string with its traceback.

        Returns:
            str: The string representation of the exception with its traceback.
        """
        return format_exception(self)
