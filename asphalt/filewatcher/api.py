from abc import abstractmethod, ABCMeta
from enum import Enum
from pathlib import Path
from typing import Union, Iterable

from typeguard import check_argument_types

from asphalt.core import Event, Signal

__all__ = ('FileEventType', 'FilesystemEvent', 'FileWatcher')


class FileEventType(Enum):
    access = 0
    attribute = 1
    create = 2
    delete = 3
    modify = 4

FileEventType.all = tuple(FileEventType.__members__.values())


class FilesystemEvent(Event):
    __slots__ = 'path'

    def __init__(self, source: 'FileWatcher', topic: str, path: Path):
        super().__init__(source, topic)
        self.path = path

    @property
    def fullpath(self) -> Path:
        return self.source.path / self.path


class FileWatcher(metaclass=ABCMeta):
    accessed = Signal(FilesystemEvent)
    created = Signal(FilesystemEvent)
    attribute_changed = Signal(FilesystemEvent)
    deleted = Signal(FilesystemEvent)
    modified = Signal(FilesystemEvent)

    def __init__(self, path: Union[str, Path], events: Iterable[FileEventType] = FileEventType.all,
                 recursive: bool = True):
        assert check_argument_types()
        self.path = Path(path)
        self.events = set(events)
        self.recursive = recursive and self.path.is_dir()
        if not events:
            raise ValueError('no watched event types specified')

    @abstractmethod
    def start(self) -> None:
        """Start watching the given file or directory for changes."""

    @abstractmethod
    def stop(self) -> None:
        """Stop watching filesystem events."""
