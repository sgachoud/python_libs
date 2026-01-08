from typing import cast


class _ImplementMeta(type):
    def __new__(mcls, name, bases, namespace):
        bases = tuple(filter(lambda b: b != _Implement, bases))
        return super().__new__(mcls, name, bases, namespace)


class _Implement(metaclass=_ImplementMeta):
    pass


class Implement[T]:
    """Use to trick the type checker that a class inherits from another class without actually doing so.
    class Cat:
      def meow(self): print("meow")

    class FakeCat(Implement(Cat)):
      def __getattr__(self, name: str):
        if name == "meow":
          return lambda: print("meow")

    fc = FakeCat()
    fc.meow() # type checker recognizes fc to have the meow method of Cat.
    print(fc.mro()) # mro does not contain Cat.
    """

    def __new__(cls, _: type[T]) -> type[T]:
        return cast(type[T], _Implement)
