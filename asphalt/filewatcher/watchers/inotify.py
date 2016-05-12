import os
import sys
from asyncio.events import get_event_loop
from pathlib import Path
from typing import Union, Iterable

from asphalt.filewatcher.api import FileWatcher, FileEventType
from asphalt.filewatcher.watchers._inotify import lib, ffi

STRUCT_SIZE = ffi.sizeof('struct inotify_event')
_mask_map = {
    FileEventType.access: lib.IN_ACCESS,
    FileEventType.attribute: lib.IN_ATTRIB,
    FileEventType.create: lib.IN_CREATE | lib.IN_MOVED_TO,
    FileEventType.delete: lib.IN_DELETE | lib.IN_DELETE_SELF | lib.IN_MOVED_FROM,
    FileEventType.modify: lib.IN_MODIFY
}
_fs_encoding = sys.getfilesystemencoding()


class INotifyFileWatcher(FileWatcher):
    def __init__(self, path: Union[str, Path], *, events: Iterable[FileEventType],
                 recursive: bool):
        super().__init__(path, events, recursive)
        self._mask = sum(value for event, value in _mask_map.items() if event in self.events)
        if recursive:
            self._mask |= lib.IN_CREATE | lib.IN_DELETE | lib.IN_MOVED_TO | lib.IN_MOVED_FROM

        self._watch_file = None
        self._watches = {}  # Dict[Path, int]
        self._reverse_watches = {}  # Dict[int, Path]

    def start(self) -> None:
        fd = lib.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            raise OSError(ffi.errno)

        # Wrap the file descriptor as a Python file object and start watching for incoming data
        self._watch_file = open(fd, 'rb')
        get_event_loop().add_reader(fd, self._event_available)

        # Add the target file or directory
        self._add_watch('')

    def stop(self) -> None:
        if self._watch_file is not None:
            get_event_loop().remove_reader(self._watch_file.fileno())
            self._watch_file.close()
            self._watch_file = None

    def _add_watch(self, relative_path: Union[str, Path]):
        path = self.path / relative_path
        paths = [path]
        if self.recursive and path.is_dir():
            for root, dirnames, _filenames in os.walk(str(path)):
                paths.extend(Path(root) / dirname for dirname in dirnames)

        for path in paths:
            pathname = path.path.encode(_fs_encoding)
            fd = lib.inotify_add_watch(self._watch_file.fileno(), pathname, self._mask)
            if fd < 0:
                raise OSError(ffi.errno)

            relative_path = path.relative_to(self.path)
            self._watches[relative_path] = fd
            self._reverse_watches[fd] = relative_path

    def _remove_watch(self, relative_path: Path) -> None:
        for path in list(self._watches):
            if relative_path == path or relative_path in path.parents:
                fd = self._watches.pop(path)
                del self._reverse_watches[fd]
                if lib.inotify_rm_watch(self._watch_file.fileno(), fd) < 0:
                    raise OSError(ffi.errno)

    def _event_available(self):
        event = ffi.new('struct inotify_event *')
        event_buffer = ffi.buffer(event)
        data = self._watch_file.read(STRUCT_SIZE)
        while data:
            event_buffer[:] = data
            relative_path = self._reverse_watches[event.wd]
            if event.len:
                raw_path = self._watch_file.read(event.len)
                filename = raw_path.rstrip(b'\x00').decode(_fs_encoding, errors='surrogatepass')
                relative_path /= filename

            fullpath = self.path / relative_path
            if event.mask & lib.IN_ACCESS and FileEventType.access in self.events:
                self.accessed.dispatch(relative_path)

            if event.mask & lib.IN_ATTRIB and FileEventType.attribute in self.events:
                self.attribute_changed.dispatch(relative_path)

            if event.mask & (lib.IN_CREATE | lib.IN_MOVED_TO):
                if self.recursive and fullpath.is_dir():
                    # Start watching this subdirectory
                    self._add_watch(relative_path)

                if FileEventType.create in self.events:
                    self.created.dispatch(relative_path)

            if event.mask & (lib.IN_DELETE | lib.IN_DELETE_SELF | lib.IN_MOVED_FROM):
                if self.recursive and relative_path in self._watches:
                    # Remove watches matching this directory and its subdirectories
                    self._remove_watch(relative_path)

                if FileEventType.delete in self.events:
                    self.deleted.dispatch(relative_path)

            if event.mask & lib.IN_MODIFY and FileEventType.modify in self.events:
                self.modified.dispatch(relative_path)

            data = self._watch_file.read(STRUCT_SIZE)
