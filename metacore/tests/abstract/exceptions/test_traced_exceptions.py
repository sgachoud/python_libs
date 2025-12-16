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
Description: Tests for the TracedException class.
🦙

Note: written with the assistance of ChatGPT from OpenAI and Claude AI.
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

import traceback
from unittest.mock import MagicMock, patch

import pytest

# Assuming the original code is in a file called exception_utils.py
# from exception_utils import format_exception, TracedException


# For testing purposes, I'll include the original code here
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


class TestFormatException:
    """Test cases for the format_exception function."""

    def test_format_exception_with_simple_exception(self):
        """Test formatting a simple exception with traceback."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "ValueError: Test error message" in result
            assert "Traceback" in result
            assert "test_format_exception_with_simple_exception" in result

    def test_format_exception_with_nested_exception(self):
        """Test formatting an exception that occurs within nested function calls."""

        def inner_function():
            raise RuntimeError("Inner error")

        def outer_function():
            inner_function()

        try:
            outer_function()
        except RuntimeError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "RuntimeError: Inner error" in result
            assert "inner_function" in result
            assert "outer_function" in result

    def test_format_exception_with_no_traceback(self):
        """Test formatting an exception that has no traceback."""
        e = ValueError("No traceback")
        # This exception wasn't raised, so it has no traceback
        result = format_exception(e)

        assert isinstance(result, str)
        assert "ValueError: No traceback" in result

    def test_format_exception_with_custom_exception(self):
        """Test formatting a custom exception class."""

        class CustomError(Exception):
            """Test"""

        try:
            raise CustomError("Custom error message")
        except CustomError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "CustomError: Custom error message" in result
            assert "Traceback" in result

    def test_format_exception_with_exception_chain(self):
        """Test formatting an exception with a cause chain."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Chained error") from e
        except RuntimeError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "RuntimeError: Chained error" in result
            assert "ValueError: Original error" in result

    def test_format_exception_with_unicode_message(self):
        """Test formatting an exception with unicode characters."""
        try:
            raise ValueError("Unicode error: 日本語 🚀")
        except ValueError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "ValueError: Unicode error: 日本語 🚀" in result

    def test_format_exception_empty_message(self):
        """Test formatting an exception with empty message."""
        try:
            raise ValueError("")
        except ValueError as e:
            result = format_exception(e)

            assert isinstance(result, str)
            assert "ValueError" in result

    @patch("traceback.format_exception")
    def test_format_exception_calls_traceback_format_exception(
        self, mock_format: MagicMock
    ):
        """Test that format_exception properly calls traceback.format_exception."""
        mock_format.return_value = ["Mocked traceback"]

        try:
            raise ValueError("Test")
        except ValueError as e:
            result = format_exception(e)

            mock_format.assert_called_once_with(type(e), e, e.__traceback__)
            assert result == "Mocked traceback"


class TestTracedException:
    """Test cases for the TracedException class."""

    def test_traced_exception_inheritance(self):
        """Test that TracedException inherits from Exception."""
        assert issubclass(TracedException, Exception)

    def test_traced_exception_can_be_raised(self):
        """Test that TracedException can be raised and caught."""
        with pytest.raises(TracedException):
            raise TracedException("Test message")

    def test_traced_exception_with_message(self):
        """Test TracedException with a message."""
        message = "Test traced exception"

        try:
            raise TracedException(message)
        except TracedException as e:
            assert str(e) == message

    def test_traceback_format_method(self):
        """Test the traceback_format method."""
        try:
            raise TracedException("Test error")
        except TracedException as e:
            result = e.traceback_format()

            assert isinstance(result, str)
            assert "TracedException: Test error" in result
            assert "Traceback" in result
            assert "test_traceback_format_method" in result

    def test_traceback_format_vs_format_exception(self):
        """Test that traceback_format produces the same result as format_exception."""
        try:
            raise TracedException("Consistency test")
        except TracedException as e:
            format_result = format_exception(e)
            method_result = e.traceback_format()

            assert format_result == method_result

    def test_traced_exception_subclass(self):
        """Test that subclasses of TracedException work correctly."""

        class CustomTracedException(TracedException):
            """Test"""

        try:
            raise CustomTracedException("Custom traced error")
        except CustomTracedException as e:
            result = e.traceback_format()

            assert isinstance(result, str)
            assert "CustomTracedException: Custom traced error" in result

    def test_traced_exception_with_args(self):
        """Test TracedException with multiple arguments."""
        try:
            raise TracedException("Error", 42, "additional info")
        except TracedException as e:
            result = e.traceback_format()

            assert isinstance(result, str)
            assert "TracedException" in result
            # The exact string representation depends on Python version
            assert "Error" in result or "('Error', 42, 'additional info')" in result

    def test_traced_exception_nested_calls(self):
        """Test TracedException in nested function calls."""

        def level3():
            raise TracedException("Deep error")

        def level2():
            level3()

        def level1():
            level2()

        try:
            level1()
        except TracedException as e:
            result = e.traceback_format()

            assert isinstance(result, str)
            assert "level1" in result
            assert "level2" in result
            assert "level3" in result
            assert "Deep error" in result

    @patch("traceback.format_exception")
    def test_traceback_format_calls_format_exception(self, mock_format: MagicMock):
        """Test that traceback_format internally calls format_exception."""
        mock_format.return_value = ["Mocked output"]

        try:
            raise TracedException("Test")
        except TracedException as e:
            result = e.traceback_format()

            mock_format.assert_called_once_with(type(e), e, e.__traceback__)
            assert result == "Mocked output"


class TestIntegration:
    """Integration tests for the exception formatting functionality."""

    def test_format_exception_and_traced_exception_integration(self):
        """Test that both functions work together correctly."""
        # Test format_exception with TracedException
        try:
            raise TracedException("Integration test")
        except TracedException as e:
            format_result = format_exception(e)
            method_result = e.traceback_format()

            assert format_result == method_result
            assert "TracedException: Integration test" in format_result

    def test_real_world_scenario(self):
        """Test a real-world scenario with multiple exception types."""

        def process_data(data: str) -> str:
            if not data:
                raise TracedException("No data provided")
            if len(data) > 100:
                raise ValueError("Data too large")
            return data.upper()

        # Test with TracedException
        try:
            process_data("")
        except TracedException as e:
            result = e.traceback_format()
            assert "No data provided" in result
            assert "process_data" in result

        # Test with regular Exception using format_exception
        try:
            process_data("x" * 101)
        except ValueError as e:
            result = format_exception(e)
            assert "Data too large" in result
            assert "process_data" in result

    def test_exception_handling_robustness(self):
        """Test that the functions handle edge cases gracefully."""
        # Test with None traceback (shouldn't happen in normal use)
        e = Exception("Test")
        result = format_exception(e)
        assert isinstance(result, str)

        # Test TracedException without being raised
        te = TracedException("Not raised")
        result = te.traceback_format()
        assert isinstance(result, str)
