from typing import Any, TypeVar, Type, overload

T = TypeVar('T')

class ZERP(object):
    @overload
    def get_model(self, model: str) -> Any: ...
    @overload
    def get_model(self, model: Type[T]) -> T: ...

    # Alias
    get = get_model