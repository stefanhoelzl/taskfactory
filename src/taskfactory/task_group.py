import contextlib
import functools
from typing import (
    Any,
    Callable,
    ContextManager,
    Iterator,
    List,
    MutableSet,
    NoReturn,
    Optional,
    TypeVar,
)

import typer

from taskfactory.console import stdout

TaskFunctionType = TypeVar("TaskFunctionType", bound=Callable[..., Any])


class TaskGroup:
    def __init__(self) -> None:
        # callback argument is required
        #  https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-one-callback
        self._app = typer.Typer(callback=lambda: None)
        self._pre_tasks: List[Callable[[], Any]] = []
        self._post_tasks: List[Callable[[], Any]] = []
        self._pre_post_task_handler: MutableSet[
            Callable[[], ContextManager[None]]
        ] = set()
        self.parents: MutableSet[TaskGroup] = set()

    def register_pre_post_task_handler(
        self, handler: Callable[[], ContextManager[None]]
    ) -> None:
        self._pre_post_task_handler.add(handler)

    def add_group(self, name: str, group: "TaskGroup") -> None:
        self._app.add_typer(group._app, name=name)
        group.register_pre_post_task_handler(self.pre_post_task_handler)

    def pre(
        self, cached: bool = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            self._pre_tasks.append(fn)
            return fn

        return self._decorator_factory(cached, decorator)

    def post(
        self, cached: bool = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            self._post_tasks.append(fn)
            return fn

        return self._decorator_factory(cached, decorator)

    def task(
        self, cached: bool = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            fn = self._with_pre_and_post_tasks(fn)
            self._app.command()(self._with_return_value_as_output(fn))
            return fn

        return self._decorator_factory(cached, decorator)

    @contextlib.contextmanager
    def pre_post_task_handler(self) -> Iterator[None]:
        stack = contextlib.ExitStack()
        for handler in self._pre_post_task_handler:
            stack.enter_context(handler())
        with stack:
            for task in self._pre_tasks:
                task()
            yield
            for task in self._post_tasks:
                task()

    def __call__(self, args: Optional[List[str]] = None) -> NoReturn:  # type: ignore
        self._app(args)

    def _decorator_factory(
        self,
        cached: bool,
        custom_decorator: Callable[[TaskFunctionType], TaskFunctionType],
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            if cached:
                fn = functools.lru_cache(maxsize=None, typed=True)(fn)  # type: ignore
            return custom_decorator(fn)

        return decorator

    def _with_pre_and_post_tasks(
        self, fn: Callable[[TaskFunctionType], TaskFunctionType]
    ) -> TaskFunctionType:
        @functools.wraps(fn)
        def with_pre_and_post_tasks(*args: Any, **kwargs: Any) -> Any:
            with self.pre_post_task_handler():
                return fn(*args, **kwargs)

        return with_pre_and_post_tasks  # type: ignore

    def _with_return_value_as_output(
        self, fn: Callable[[TaskFunctionType], TaskFunctionType]
    ) -> TaskFunctionType:
        @functools.wraps(fn)
        def with_return_value_as_output(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            if result is not None:
                stdout.print(result)
            return result

        return with_return_value_as_output  # type: ignore
