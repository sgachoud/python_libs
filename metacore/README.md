# metacore

> **⚠️ EARLY ALPHA WARNING**: This library is in early development and the API may change significantly between versions. Use at your own risk in production environments.

A sophisticated type system enhancement library for Python metaprogramming and runtime behavior modification.

## Overview

`metacore` bridges the gap between static type hints and runtime behavior by making types first-class citizens in the runtime environment. It provides powerful tools for:

- **Immutable constant namespaces** with automatic type coercion
- **Extensible type annotation processing** via registry pattern
- **Enhanced exception handling** with formatted tracebacks
- **Runtime type validation and conversion**

## Imports and layout

Import everyday tools directly from `metacore`:

```python
from metacore import (
    ConstantNamespace,
    TracedException,
    ValidationLevel,
    annotation_registry,
    convert_to_annotation,
    converter_from_annotation,
    default_from_annotation,
    defaulter_from_annotation,
    validate_from_annotation,
    validator_from_annotation,
)
```

Use feature modules for extension interfaces, type helpers, and errors:

```python
from metacore.annotations import AnnotationsRegistry, AnnotationEntry, HousingAnnotationEntry, CastType
from metacore.constants import ConstantsMetaclass
from metacore.exceptions import ConstantsModificationError, ConvertingToAnnotationTypeError
from metacore.typing import Implement, is_optional, is_union, resolve_annotation_types
```

```text
src/metacore/
├── __init__.py          # Common public imports
├── constants.py         # Constant namespaces and their metaclass
├── exceptions.py        # Exception hierarchy and traceback formatting
├── typing.py            # Annotation inspection helpers and Implement
├── py.typed             # Type information for package consumers
└── annotations/
    ├── __init__.py      # Public annotation API
    ├── _api.py          # Shared registry and convenience functions
    ├── _registry.py     # Registry implementation
    ├── _entries.py      # Custom processor interfaces
    ├── _builtins.py     # Built-in handlers and explicit registration
    └── _types.py        # Validation levels, CastType, and callable aliases
```

Modules beginning with `_` are implementation details. Each public module declares
its exports with `__all__`. The former `meta`, `abstract`, `annotations_processors`,
and `typing_utilities` import paths have been removed.

`annotation_registry()` returns the shared default registry. Construct
`AnnotationsRegistry()` for an independent registry with its own built-in handlers
and customizations. Neither requires importing a handler module first.

## Features

### ConstantNamespace

Create immutable constant namespaces with automatic type coercion at class definition time:

```python
from metacore import ConstantNamespace
import pathlib

class MyConstants(ConstantNamespace):
    # Regular attributes (not annotated) are not constants
    A = 1

    # Annotated attributes become immutable constants
    B: int = 2
    C: int = 3.4  # Coerced to 3

    # Advanced type coercion
    path: pathlib.Path = "documents/test.txt"  # Coerced to Path object
    numbers: list[int] = [1, 1.5, 3]  # Coerced to [1, 1, 3]

# Access constants
print(MyConstants.B)  # 2
print(MyConstants.path)  # PosixPath('documents/test.txt')

# Modification is prevented
MyConstants.C = 10  # Raises ConstantsModificationError

# Dict-like interface
MyConstants.items()  # [('B', 2), ('C', 3), ...]
MyConstants.keys()   # ('B', 'C', 'path', 'numbers')
MyConstants.get('B', default=0)  # 2
```

### Type Annotation Processing

Extensible registry-based type processing system:

```python
from metacore.annotations import (
    annotation_registry,
    HousingAnnotationEntry,
)

registry = annotation_registry()

# Convert values to match type annotations
result = registry.convert_to_annotation(list[int], ("42", 4.2))  # Returns [42, 4]

# Register a custom type handler
class MyCustomType:
    def __init__(self, value):
        self.value = value

registry.register_processor(
    MyCustomType,
    HousingAnnotationEntry(converter=MyCustomType),
)
custom = registry.convert_to_annotation(MyCustomType, "value")
```

### Enhanced Exceptions

All library exceptions inherit from `TracedException` for better debugging:

```python
from metacore import TracedException

class MyError(TracedException):
    """Custom exception with formatted traceback"""
```

## Installation

```bash
pip install sg-metacore
```

## Requirements

- Python 3.12 or higher

## Development Status

This library is in **active alpha development**. Breaking changes may occur between minor versions.

From the `metacore` project directory, install the development dependencies and run
the tests:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Tests use the public package imports. Pytest also adds `src` to the import path for
local development without an editable installation.

### Roadmap

tbd

## Contributing

This is an early-stage project. Contributions, bug reports, and feedback are welcome but please be aware of the alpha status.

## License

MIT License - see LICENSE file for details.

## Author

Sébastien Gachoud

---

**Note**: Some code and tests were developed with assistance from Claude AI.
