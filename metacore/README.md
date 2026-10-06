# metacore

> **⚠️ EARLY ALPHA WARNING**: This library is in early development and the API may change significantly between versions. Use at your own risk in production environments.

A sophisticated type system enhancement library for Python metaprogramming and runtime behavior modification.

## Overview

`metacore` bridges the gap between static type hints and runtime behavior by making types first-class citizens in the runtime environment. It provides powerful tools for:

- **Immutable constant namespaces** with automatic type coercion
- **Extensible type annotation processing** via registry pattern
- **Enhanced exception handling** with formatted tracebacks
- **Runtime type validation and conversion**

## Features

### ConstantNamespace

Create immutable constant namespaces with automatic type coercion at class definition time:

```python
from metacore.meta.classes.constants import ConstantNamespace
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
from metacore.meta.typing_utilities.annotations_processors.processors import (
    annotation_registry,
    ValidationLevel
)

registry = annotation_registry()

# Convert values to match type annotations
result = registry.convert_to_annotation(list[int], ("42", 4.2))  # Returns [42, 4]

# Register custom type handlers
@registry.register_processor(MyCustomType)
def process_custom_type(value, annotation):
    # Custom conversion logic
    return MyCustomType(value)
```

### Enhanced Exceptions

All library exceptions inherit from `TracedException` for better debugging:

```python
from metacore.abstract.exceptions.traced_exceptions import TracedException

class MyError(TracedException):
    """Custom exception with formatted traceback"""
    pass
```

## Installation

```bash
pip install metacore
```

## Requirements

- Python 3.12 or higher

## Development Status

This library is in **active alpha development**. The current focus is on refactoring the annotation processing system into a modular architecture. Breaking changes may occur between minor versions.

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
