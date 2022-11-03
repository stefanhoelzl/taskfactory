from cleo.io.io import IO
from poetry.plugins.plugin import Plugin
from poetry.poetry import Poetry
from tools import release


class VersionPlugin(Plugin):
    def activate(self, poetry: Poetry, io: IO) -> None:
        version = release.version()
        io.write_line(f"Version: {version}")
        poetry.package.version = version
