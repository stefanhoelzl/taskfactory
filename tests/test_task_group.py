from types import TracebackType
from typing import List, NamedTuple, NoReturn

import pytest

from taskfactory import TaskGroup, stderr, stdout


class Result(NamedTuple):
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def run(group: TaskGroup, args: List[str]) -> Result:
    try:
        with stderr.capture() as err, stdout.capture() as out:
            group(args)
    except SystemExit as e:
        return Result(e.code, out.get(), err.get())


def test_simple_task() -> None:
    group = TaskGroup()

    @group.task()
    def task(string: str, integer: int = 0) -> None:
        stdout.print(string, integer)

    assert run(group, ["task", "string", "--integer=1"]) == Result(
        exit_code=0, stdout="string 1\n"
    )


def test_sub_groups() -> None:
    sub = TaskGroup()

    group = TaskGroup()
    group.add_group("sub", sub)

    @sub.task()
    def task(string: str, integer: int = 0) -> None:
        stdout.print(string, integer)

    assert run(group, ["sub", "task", "string", "--integer=1"]) == Result(
        exit_code=0, stdout="string 1\n"
    )


def test_cached_tasks_only_runs_once() -> None:
    group = TaskGroup()

    @group.task(cached=True)
    def cached() -> None:
        stdout.print("cached")

    @group.task()
    def main() -> None:
        cached()
        cached()

    assert run(group, ["main"]) == Result(exit_code=0, stdout="cached\n")


def test_pre_post_tasks_from_group() -> None:
    group = TaskGroup()

    @group.pre()
    def pre() -> None:
        stdout.print("pre")

    @group.post()
    def post() -> None:
        stdout.print("post")

    @group.task()
    def task() -> None:
        stdout.print("task")

    assert run(group, ["task"]) == Result(exit_code=0, stdout="pre\ntask\npost\n")


def test_pre_post_tasks_from_parent_group() -> None:
    parent = TaskGroup()
    sub = TaskGroup()
    parent.add_group("sub", sub)

    @sub.task()
    def task() -> None:
        stdout.print("task")

    @parent.pre()
    def pre() -> None:
        stdout.print("pre")

    @parent.post()
    def post() -> None:
        stdout.print("post")

    assert run(sub, ["task"]) == Result(exit_code=0, stdout="pre\ntask\npost\n")


def test_print_return_value() -> None:
    group = TaskGroup()

    @group.task()
    def sub() -> str:
        return "task"

    @group.task()
    def task() -> str:
        return sub()

    assert run(group, ["task"]) == Result(exit_code=0, stdout="task\n")


def test_exception_handler() -> None:
    class Base(Exception):
        pass

    class Sub(Base):
        pass

    parent = TaskGroup()
    sub = TaskGroup()
    parent.add_group("sub", sub)

    @parent.exception_handler(Base)
    def handle_runtime_error(exception: Base, traceback: TracebackType) -> int:
        stderr.print("handled")
        return 99

    @sub.task()
    def handled() -> NoReturn:
        raise Sub()

    assert run(sub, ["handled"]) == Result(exit_code=99, stderr="handled\n")

    @sub.task()
    def unhandled() -> NoReturn:
        raise RuntimeError()

    with pytest.raises(RuntimeError):
        run(sub, ["unhandled"])


def test_skipping_tasks() -> None:
    group = TaskGroup()

    @group.task(skip=True)
    def boolean() -> None:
        stdout.print("skipped")

    assert run(group, ["boolean"]) == Result(exit_code=0)

    @group.task(skip=lambda: True)
    def fn() -> None:
        stdout.print("skipped")

    assert run(group, ["fn"]) == Result(exit_code=0)
