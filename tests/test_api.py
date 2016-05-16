from pathlib import Path

from asphalt.filewatcher.api import FilesystemEvent, FileWatcher


class DummyFileWatcher(FileWatcher):
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def test_fullpath():
    root = Path('/foo')
    event = FilesystemEvent(DummyFileWatcher(root), 'created', root / 'file.dat')
    assert event.fullpath == Path('/foo/file.dat')
