import functools
from abc import ABC, abstractmethod
from typing import Any, Callable


class IAsyncExecutor(ABC):

    @abstractmethod
    async def __call__(self, func: Callable) -> Any: ...


def cpu_bound(func):
    """
    Mark functions explicitly as cpu_bound
    """

    @functools.wraps(func)
    def wrapper_cpu_bound(*args, **kwargs):
        func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper_cpu_bound
