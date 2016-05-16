import logging
import sys
from asyncio import get_event_loop, CancelledError
from pathlib import Path
from typing import Union, Iterable

from asyncio_extras.threads import call_in_executor

from asphalt.filewatcher.api import FileWatcher, FileEventType
from asphalt.filewatcher.watchers._windows import ffi, lib

logger = logging.getLogger(__name__)
_mask_map = {
    FileEventType.create: lib.FILE_NOTIFY_CHANGE_FILE_NAME | lib.FILE_NOTIFY_CHANGE_DIR_NAME,
    FileEventType.delete: lib.FILE_NOTIFY_CHANGE_FILE_NAME | lib.FILE_NOTIFY_CHANGE_DIR_NAME,
    FileEventType.modify: lib.FILE_NOTIFY_CHANGE_LAST_WRITE
}
_action_map = {
    lib.FILE_ACTION_ADDED: FileEventType.create,
    lib.FILE_ACTION_RENAMED_NEW_NAME: FileEventType.create,
    lib.FILE_ACTION_REMOVED: FileEventType.delete,
    lib.FILE_ACTION_RENAMED_OLD_NAME: FileEventType.delete,
    lib.FILE_ACTION_MODIFIED: FileEventType.modify
}
_fs_encoding = sys.getfilesystemencoding()
NOTIFY_STRUCT_SIZE = ffi.sizeof('FILE_NOTIFY_INFORMATION')


class WindowsFileWatcher(FileWatcher):
    def __init__(self, path: Union[str, Path], *, events: Iterable[FileEventType],
                 recursive: bool):
        super().__init__(path, events, recursive)
        self._poll_task = None
        self._overlapped_buffer = ffi.new('LPOVERLAPPED')
        self._mask = 0
        for event, value in _mask_map.items():
            if event in self.events:
                self._mask |= _mask_map.get(event, 0)

    def start(self) -> None:
        handle = lib.CreateFile(
            str(self.path),
            lib.FILE_LIST_DIRECTORY,
            lib.FILE_SHARE_READ | lib.FILE_SHARE_WRITE | lib.FILE_SHARE_DELETE,
            ffi.NULL,
            lib.OPEN_EXISTING,
            lib.FILE_FLAG_BACKUP_SEMANTICS | lib.FILE_FLAG_OVERLAPPED,
            ffi.NULL
        )
        if not handle:
            code, message = ffi.getwinerror()
            raise OSError(ffi.errno, message, str(self.path), code)

        self._poll_task = get_event_loop().create_task(self._read_events(handle))

    def stop(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None

    async def _read_events(self, dir_handle):
        notify_info_buffer = ffi.new('char[16384]')
        num_readbytes_buf = ffi.new('LPDWORD')
        while True:
            retval = lib.ReadDirectoryChangesW(
                dir_handle, notify_info_buffer, len(notify_info_buffer),
                self.recursive, self._mask, num_readbytes_buf, self._overlapped_buffer,
                ffi.NULL)
            if not retval:
                code, message = ffi.getwinerror()
                if code not in (lib.ERROR_SUCCESS, lib.ERROR_OPERATION_ABORTED):
                    logging.error('error calling ReadDirectoryChangesW(): %d (%s)', code, message)
                break

            try:
                retval = await call_in_executor(
                    lib.GetOverlappedResult, dir_handle, self._overlapped_buffer,
                    num_readbytes_buf, True)
            except CancelledError:
                lib.CancelIoEx(dir_handle, self._overlapped_buffer)
                break

            if not retval:
                code, message = ffi.getwinerror()
                if code not in (lib.ERROR_SUCCESS, lib.ERROR_OPERATION_ABORTED):
                    logging.error('error calling GetOverlappedResult(): %d (%s)', code, message)
                break

            offset = 0
            while True:
                notify_info = ffi.cast('FILE_NOTIFY_INFORMATION *',
                                       notify_info_buffer[offset:offset + NOTIFY_STRUCT_SIZE])
                event_type = _action_map[notify_info.Action]
                pathname = ffi.string(notify_info.FileName, notify_info.FileNameLength)
                if event_type in self.events:
                    pathname = ffi.string(notify_info.FileName, notify_info.FileNameLength)
                    path = Path(pathname)
                    if notify_info.Action in (
                            lib.FILE_ACTION_ADDED, lib.FILE_ACTION_RENAMED_NEW_NAME):
                        self.created.dispatch(path)
                    elif notify_info.Action in (
                            lib.FILE_ACTION_REMOVED, lib.FILE_ACTION_RENAMED_OLD_NAME):
                        self.deleted.dispatch(path)
                    elif notify_info.Action == lib.FILE_ACTION_MODIFIED:
                        self.modified.dispatch(path)

                if notify_info.NextEntryOffset:
                    offset = notify_info.NextEntryOffset
                else:
                    break

        lib.CloseHandle(dir_handle)
