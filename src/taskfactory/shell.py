import contextlib
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator, List, Union

from .console import stderr, stdout


@contextlib.contextmanager
def cd(path: Union[Path, str]) -> Iterator[None]:
    old_path = Path.cwd()
    os.chdir(path)
    yield
    os.chdir(old_path)


def run(cmd: str) -> None:
    result = subprocess.run(shlex.split(cmd))
    if result.returncode != 0:
        sys.exit(result.returncode)


def concurrent(cmds: List[str]) -> None:
    failures = 0
    with ThreadPoolExecutor() as pool:
        processes = [
            pool.submit(
                subprocess.run,
                shlex.split(cmd),
                capture_output=True,
                universal_newlines=True,
            )  # type:ignore
            for cmd in cmds
        ]
        for future in as_completed(processes):
            process: subprocess.CompletedProcess[str] = future.result()
            success = process.returncode == 0
            if not success:
                failures += 1

            stdout.rule(shlex.join(process.args), style="green" if success else "red")
            stdout.out(process.stdout)

            if process.stderr:
                stdout.rule("stderr", style="gray")
                stderr.out(process.stderr)
    if failures > 0:
        stderr.print(f"{failures} failed commands", style="red")
        sys.exit(1)
