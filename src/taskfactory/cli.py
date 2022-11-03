import os
import sys
from pathlib import Path
from typing import NoReturn, Optional

from taskfactory import TaskGroup, stderr

FAILURE_EXIT_CODE = 1

MODULE_NAME = "tasks"
GROUP_NAME = "main"


def _discover_tasks_path() -> Optional[Path]:
    path = Path().absolute()
    while path.parent != path:
        if (path / f"{MODULE_NAME}.py").is_file() or (path / MODULE_NAME).is_dir():
            return path

        path = path.parent
    return None


def _fail(msg: str) -> NoReturn:
    stderr.print(msg, style="red")
    sys.exit(1)


def main() -> NoReturn:
    tasks_path = _discover_tasks_path()
    if tasks_path is None:
        _fail(f"No {MODULE_NAME} module found!")

    sys.path.insert(0, str(tasks_path))
    import tasks

    try:
        group: TaskGroup = getattr(tasks, GROUP_NAME)
    except AttributeError:
        _fail(f"No {GROUP_NAME} found in {MODULE_NAME} module!")

    if not isinstance(group, TaskGroup):
        _fail(f"{GROUP_NAME} is not a {TaskGroup.__name__}!")

    os.chdir(str(tasks_path))
    group()
