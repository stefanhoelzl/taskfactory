import sys

from rich.console import Console as RichConsole

stdout = RichConsole(file=sys.stdout)
stderr = RichConsole(file=sys.stderr)
