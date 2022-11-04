import contextlib
import functools
import sys
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    MutableSet,
    NoReturn,
    Optional,
    Type,
    TypeVar,
    Union,
)

import typer

from taskfactory.console import stdout

TaskFunctionType = TypeVar("TaskFunctionType", bound=Callable[..., Any])
ExceptionType = TypeVar("ExceptionType", bound=Exception)
Skip = Union[bool, Callable[[], bool]]


class TaskGroup:
    def __init__(self) -> None:
        # callback argument is required
        #  https://typer.tiangolo.com/tutorial/commands/one-or-multiple/#one-command-and-one-callback
        self._app = typer.Typer(callback=lambda: None)
        self._pre_tasks: List[Callable[[], Any]] = []
        self._post_tasks: List[Callable[[], Any]] = []
        self._exception_handlers: Dict[
            Type[Exception], Callable[[Exception, TracebackType], int]
        ] = {}
        self.parents: MutableSet[TaskGroup] = set()

    def exception_handler(
        self, exception_type: Type[ExceptionType]
    ) -> Callable[[Callable[[ExceptionType, TracebackType], int]], None]:
        def decorator(fn: Callable[[ExceptionType, TracebackType], int]) -> None:
            self._exception_handlers[exception_type] = fn  # type: ignore

        return decorator

    def add_group(self, name: str, group: "TaskGroup") -> None:
        self._app.add_typer(group._app, name=name)
        group.parents.add(self)

    def pre(
        self, cached: bool = False, skip: Skip = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            self._pre_tasks.append(fn)
            return fn

        return self._decorator_factory(cached, skip, decorator)

    def post(
        self, cached: bool = False, skip: Skip = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            self._post_tasks.append(fn)
            return fn

        return self._decorator_factory(cached, skip, decorator)

    def task(
        self, cached: bool = False, skip: Skip = False
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            fn = self._with_pre_and_post_tasks(fn)
            self._app.command()(
                self._with_return_value_as_output(self._with_exception_handler(fn))
            )
            return fn

        return self._decorator_factory(cached, skip, decorator)

    @contextlib.contextmanager
    def pre_post_task_handler(self) -> Iterator[None]:
        stack = contextlib.ExitStack()
        for parent in self.parents:
            stack.enter_context(parent.pre_post_task_handler())
        with stack:
            for task in self._pre_tasks:
                task()
            yield
            for task in self._post_tasks:
                task()

    def handle_exception(self, exception: Exception) -> NoReturn:
        handler = next(
            (
                h
                for t, h in self._exception_handlers.items()
                if isinstance(exception, t)
            ),
            None,
        )
        if handler is None:
            for parent in self.parents:
                parent.handle_exception(exception)
            raise

        _, _, tb = sys.exc_info()
        assert tb is not None

        exit_code = handler(exception, tb)
        sys.exit(exit_code)

    def __call__(self, args: Optional[List[str]] = None) -> NoReturn:  # type: ignore
        self._app(args)

    def _decorator_factory(
        self,
        cached: bool,
        skip: Skip,
        custom_decorator: Callable[[TaskFunctionType], TaskFunctionType],
    ) -> Callable[[TaskFunctionType], TaskFunctionType]:
        def decorator(fn: TaskFunctionType) -> TaskFunctionType:
            fn = self._maybe_skipped(fn, skip)
            if cached:
                fn = functools.lru_cache(maxsize=None, typed=True)(fn)  # type: ignore
            return custom_decorator(fn)

        return decorator

    def _maybe_skipped(
        self, fn: Callable[[TaskFunctionType], TaskFunctionType], skip: Skip
    ) -> TaskFunctionType:
        @functools.wraps(fn)
        def maybe_skipped(*args: Any, **kwargs: Any) -> Any:
            if (skip if isinstance(skip, bool) else skip()) is not True:
                return fn(*args, **kwargs)
            return None

        return maybe_skipped  # type: ignore

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

    def _with_exception_handler(
        self, fn: Callable[[TaskFunctionType], TaskFunctionType]
    ) -> TaskFunctionType:
        @functools.wraps(fn)
        def with_exception_handler(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                self.handle_exception(exc)

        return with_exception_handler  # type: ignore
