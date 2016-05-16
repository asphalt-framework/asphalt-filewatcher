import os
import platform
import select
import sys
from asyncio import get_event_loop
from pathlib import Path
from typing import Union, Iterable

from asphalt.filewatcher.api import FileWatcher, FileEventType

O_EVTONLY = 0x8000
OPEN_FLAGS = O_EVTONLY if platform.system() == 'Darwin' else (os.O_RDONLY | os.O_NONBLOCK)
_mask_map = {
    FileEventType.attribute: select.KQ_NOTE_ATTRIB,
    FileEventType.create: select.KQ_NOTE_EXTEND | select.KQ_NOTE_RENAME,
    FileEventType.delete: select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME,
    FileEventType.modify: select.KQ_NOTE_WRITE
}
_fs_encoding = sys.getfilesystemencoding()


class KQueueFileWatcher(FileWatcher):
    def __init__(self, path: Union[str, Path], events: Iterable[FileEventType], recursive: bool):
        super().__init__(path, events, recursive)
        self._fflags = 0
        for event in events:
            self._fflags |= _mask_map.get(event, 0)

        if recursive:
            self._fflags |= select.KQ_NOTE_WRITE | select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME

        self._kqueue = None
        self._watches = {}  # Dict[Path, int]
        self._reverse_watches = {}  # Dict[int, Path]

    def start(self) -> None:
        self._kqueue = select.kqueue()
        get_event_loop().add_reader(self._kqueue, self._event_available)
        self._add_watch('')

    def stop(self) -> None:
        if self._kqueue:
            get_event_loop().remove_reader(self._kqueue.fileno())
            self._kqueue.close()
            self._kqueue = None

    def _add_watch(self, relative_path: Union[str, Path]):
        path = self.path / relative_path
        paths = [path]
        if self.recursive and path.is_dir():
            for root, dirnames, _filenames in os.walk(str(path)):
                paths.extend(Path(root) / dirname for dirname in dirnames)

        events = []
        for path in paths:
            fd = os.open(str(path), OPEN_FLAGS)
            event = select.kevent(fd, select.KQ_FILTER_VNODE,
                                  select.KQ_EV_ADD | select.KQ_EV_CLEAR, self._fflags)
            events.append(event)
            relative_path = path.relative_to(self.path)
            self._watches[relative_path] = fd
            self._reverse_watches[fd] = relative_path

        self._kqueue.control(events, 0)

    def _remove_watch(self, relative_path: Path) -> None:
        for path in list(self._watches):
            if relative_path == path or relative_path in path.parents:
                fd = self._watches.pop(path)
                del self._reverse_watches[fd]
                os.close(fd)

    def _event_available(self):
        from pytest import set_trace;
        set_trace()
        for event in self._kqueue.control(None, 100):
            print(event.data)
            # relative_path = self._reverse_watches[event.wd]
            # if event.len:
            #     raw_path = self._watch_file.read(event.len)
            #     filename = raw_path.rstrip(b'\x00').decode(_fs_encoding, errors='surrogatepass')
            #     relative_path /= filename
            #
            # fullpath = self.path / relative_path
            # if event.mask & lib.IN_ACCESS and FileEventType.access in self.events:
            #     self.accessed.dispatch(relative_path)
            #
            # if event.mask & lib.IN_ATTRIB and FileEventType.attribute in self.events:
            #     self.attribute_changed.dispatch(relative_path)
            #
            # if event.mask & (lib.IN_CREATE | lib.IN_MOVED_TO):
            #     if self.recursive and fullpath.is_dir():
            #         # Start watching this subdirectory
            #         self._add_watch(relative_path)
            #
            #     if FileEventType.create in self.events:
            #         self.created.dispatch(relative_path)
            #
            # if event.mask & (lib.IN_DELETE | lib.IN_DELETE_SELF | lib.IN_MOVED_FROM):
            #     if self.recursive and relative_path in self._watches:
            #         # Remove watches matching this directory and its subdirectories
            #         self._remove_watch(relative_path)
            #
            #     if FileEventType.delete in self.events:
            #         self.deleted.dispatch(relative_path)
            #
            # if event.mask & lib.IN_MODIFY and FileEventType.modify in self.events:
            #     self.modified.dispatch(relative_path)
