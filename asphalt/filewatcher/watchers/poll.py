import os
from asyncio import get_event_loop, sleep
from numbers import Real
from os import stat_result
from pathlib import Path
from typing import Union, Dict, Iterable

from asyncio_extras.threads import call_in_executor
from typeguard import check_argument_types

from asphalt.filewatcher.api import FileWatcher, FileEventType


class PollingFileWatcher(FileWatcher):
    def __init__(self, path: Union[str, Path], interval: Real, *,
                 events: Iterable[FileEventType] = FileEventType.all, recursive: bool = True):
        assert check_argument_types()
        super().__init__(path, events, recursive)
        self.interval = interval
        self._poll_task = None
        self._old_stats = self._old_files = None

    def start(self) -> None:
        self._old_stats = self._collect_stats()
        self._old_files = frozenset(self._old_stats)
        self._poll_task = get_event_loop().create_task(self._poll_files())

    def stop(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None

    def _collect_stats(self) -> Dict[Path, stat_result]:
        paths = [self.path]
        if self.path.is_dir():
            if self.recursive:
                for root, dirnames, filenames in os.walk(str(self.path)):
                    paths.extend(Path(root).joinpath(name).relative_to(self.path) for
                                 name in dirnames + filenames)
            else:
                paths.extend(self.path.iterdir())

        return {path: self.path.joinpath(path).stat() for path in paths}

    async def _poll_files(self):
        while True:
            await sleep(self.interval)
            new_stats = await call_in_executor(self._collect_stats)
            new_files = frozenset(new_stats)

            # Check for any new files
            if FileEventType.create in self.events:
                for path in sorted(new_files - self._old_files):
                    self.created.dispatch(path)

            # Check for deleted files
            if FileEventType.delete in self.events:
                for path in sorted(self._old_files - new_files):
                    self.deleted.dispatch(path)

            # Check for modified files
            if {FileEventType.modify, FileEventType.attribute, FileEventType.access} & self.events:
                for path in sorted(self._old_files & new_files):
                    old = self._old_stats[path]
                    new = new_stats[path]

                    # Check for differences in access time
                    if FileEventType.access in self.events:
                        if old.st_atime_ns != new.st_atime_ns:
                            self.accessed.dispatch(path)

                    # Check for differences in mode, owner and group
                    if FileEventType.attribute in self.events:
                        if (old.st_mode != new.st_mode or old.st_uid != new.st_uid or
                                old.st_gid != new.st_gid):
                            self.attribute_changed.dispatch(path)

                    # Check for differences in modification time and size
                    if FileEventType.modify in self.events:
                        if old.st_mtime_ns != new.st_mtime_ns or old.st_size != new.st_size:
                            self.modified.dispatch(path)

            self._old_stats = new_stats
            self._old_files = new_files
