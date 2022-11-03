import io
from contextlib import redirect_stderr, redirect_stdout
from typing import List, NamedTuple

from taskfactory import TaskGroup


class Result(NamedTuple):
    exit_code: int
    stdout: str = ""
    stderr: str = ""


def run(group: TaskGroup, args: List[str]) -> Result:
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        with redirect_stderr(stderr), redirect_stdout(stdout):
            group(args)
    except SystemExit as e:
        return Result(e.code, stdout.getvalue(), stderr.getvalue())


def test_simple_task() -> None:
    group = TaskGroup()

    @group.task()
    def task(string: str, integer: int = 0) -> None:
        print(string, integer)

    assert run(group, ["task", "string", "--integer=1"]) == Result(
        exit_code=0, stdout="string 1\n"
    )


def test_sub_groups() -> None:
    sub = TaskGroup()

    group = TaskGroup()
    group.add_group("sub", sub)

    @sub.task()
    def task(string: str, integer: int = 0) -> None:
        print(string, integer)

    assert run(group, ["sub", "task", "string", "--integer=1"]) == Result(
        exit_code=0, stdout="string 1\n"
    )
