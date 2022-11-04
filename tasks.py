import os

from taskfactory import TaskGroup, shell

main = TaskGroup()


@main.task()
def lint(check: bool = False) -> None:
    check_flag = "--check" if check else ""
    shell.concurrent(
        [
            f"black {check_flag} .",
            f"isort {check_flag} .",
            "mypy --strict src tests tasks.py",
        ]
    )


@main.task()
def tests() -> None:
    shell.run("pytest -vv")


@main.task()
def check() -> None:
    tests()
    lint()
