"""Annotation processors package.

This package provides the annotation registry system for type conversion and validation.
Importing this package automatically registers built-in type handlers.
"""

# Import known_types to register built-in type handlers
from . import known_types  # noqa: F401
