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
Created: 2025-07-15
Description: This module provides tools to manage annotations and types. This includes:
            - Various free functions: is_union, is_optional, is_binary_optional,
              type_hints_from_dict
            - The annotations manager that provides tools to create default values from annotations
                and convert values to annotations. The convertions and defaulting can be extended
                with custom converters and defaulters. See register_custom_type_defaulter,
                register_custom_type_converter and register_custom_type_converter_creator
🦙
"""

__author__ = "Sébastien Gachoud"
__license__ = "MIT"

from ...abstract.exceptions.traced_exceptions import TracedException

class TypingError(TracedException):
    """General Error for this typing extension."""
