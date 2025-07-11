"""
Author: Sébastien Gachoud
Created: 2025-07-11
Description: Base class and functions to ease exception tracing in a string.
🦙
"""

__author__ = "Sébastien Gachoud"
__version__ = "1.0.0"
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
