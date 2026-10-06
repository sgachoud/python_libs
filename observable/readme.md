# observable

Observable fields with conversion, access policies, and change notifications.
Requires Python 3.13 or newer.

## Installation

Install the `sg-observable` package from PyPI:

```bash
python -m pip install sg-observable
```

Pip also installs its dependencies: `sg-metacore` from PyPI and NumPy.

## Usage

```python
from observable.observable import Observable, ObservableField, auto_field

class Counter(Observable):
    value: ObservableField[int, str] = auto_field(default=0)

counter = Counter()
counter.value = "42"       # Writes accept str and convert to int.
assert counter.value == 42 # Reads return int.
```

## Runtime and typing

`src/observable/observable.py` contains the implementation and its public type
annotations, including descriptor overloads and the types of field decorators.

`auto_field()` is intended for annotated declarations in an `Observable` class.
At runtime it returns an `AutoField` configuration that the metaclass replaces
with an `ObservableField`. Its return annotation describes that resulting
descriptor, with a localized cast in the factory to account for the metaclass
transformation and preserve the field's read and write types.
Use `AutoField` directly when working with a configuration outside a class body.

The wheel includes a `py.typed` marker so type checkers use the annotations in
the implementation. Existing comments and TODOs remain in the implementation.

## Development

From the `observable` project directory, install the development dependencies
and run the checks. MetaCore is installed as the `sg-metacore` PyPI dependency.

```bash
python -m pip install -e ".[dev]"
python -m pyright --project pyproject.toml
python -m pytest
```

The tests cover runtime behavior and rejected type errors.
Static examples under `tests/typing/` verify descriptor inference and
callback signatures.
