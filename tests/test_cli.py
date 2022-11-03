import shlex
import subprocess
import textwrap
from pathlib import Path


def run(cmd: str, cwd: Path) -> "subprocess.CompletedProcess[bytes]":
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        shell=True,  # shell=True required on Windows to find `tasks`
    )


def test_discover_tasks_in_current_directory(tmp_path: Path) -> None:
    (tmp_path / "tasks.py").write_text(
        textwrap.dedent(
            """
    from taskfactory import TaskGroup

    main = TaskGroup()

    @main.task()
    def task():
        print("task")
    """
        )
    )

    result = run("tasks task", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == b"task"


def test_discover_tasks_in_parent_directory(tmp_path: Path) -> None:
    (tmp_path / "tasks.py").write_text(
        textwrap.dedent(
            """
    from taskfactory import TaskGroup

    main = TaskGroup()

    @main.task()
    def task():
        print("task")
    """
        )
    )
    child_directory = tmp_path / "child"
    child_directory.mkdir()

    result = run("tasks task", cwd=child_directory)
    assert result.returncode == 0
    assert result.stdout.strip() == b"task"


def test_discover_tasks_module(tmp_path: Path) -> None:
    module_path = tmp_path / "tasks"
    module_path.mkdir()
    (module_path / "__init__.py").write_text("from .mod import main")

    (module_path / "mod.py").write_text(
        textwrap.dedent(
            """
    from taskfactory import TaskGroup

    main = TaskGroup()

    @main.task()
    def task():
        print("task")
    """
        )
    )

    result = run("tasks task", cwd=tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == b"task"


def test_run_from_tasks_path(tmp_path: Path) -> None:
    (tmp_path / "tasks.py").write_text(
        textwrap.dedent(
            """
    from pathlib import Path
    from taskfactory import TaskGroup

    main = TaskGroup()

    @main.task()
    def task():
        print(Path().absolute())
    """
        )
    )

    child_path = tmp_path / "child"
    child_path.mkdir()

    result = run("tasks task", cwd=child_path)
    assert result.returncode == 0
    assert result.stdout.decode().strip() == str(tmp_path.absolute())


def test_error_when_no_tasks_module_found(tmp_path: Path) -> None:
    result = run("tasks task", cwd=tmp_path)
    assert result.returncode == 1
    assert result.stderr.strip() == b"No tasks module found!"


def test_error_when_no_main_group_found(tmp_path: Path) -> None:
    (tmp_path / "tasks.py").touch()

    result = run("tasks task", cwd=tmp_path)
    assert result.returncode == 1
    assert result.stderr.strip() == b"No main found in tasks module!"


def test_error_when_main_is_no_task_group(tmp_path: Path) -> None:
    (tmp_path / "tasks.py").write_text("main = None")

    result = run("tasks task", cwd=tmp_path)
    assert result.returncode == 1
    assert result.stderr.strip() == b"main is not a TaskGroup!"
