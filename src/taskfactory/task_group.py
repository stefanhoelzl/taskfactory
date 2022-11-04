import functools
from typing import Any, Callable, List, NoReturn, Optional, TypeVar

import typer as _typer

TaskFunctionType = TypeVar("TaskFunctionType", bound=Callable[..., Any])


class TaskGroup:
    def __init__(self) -> None:
        # callback argument is required
        #  https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-one-callback
        self._app = _typer.Typer(callback=lambda: None)

    def add_group(self, name: str, group: "TaskGroup") -> None:
        self._app.add_typer(group._app, name=name)

    def task(
        self, cached: bool = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            self._app.command()(fn)
            if cached:
                return functools.cache(fn)  # type: ignore
            return fn

        return decorator

    def __call__(self, args: Optional[List[str]] = None) -> NoReturn:  # type: ignore
        self._app(args)
