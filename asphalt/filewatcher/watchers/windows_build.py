from cffi import FFI

ffi = FFI()
ffi.set_unicode(True)
ffi.set_source('asphalt.filewatcher.watchers._windows', "#include <windows.h>")
ffi.cdef("""
    #define OPEN_EXISTING ...
    #define FILE_LIST_DIRECTORY ...
    #define FILE_SHARE_READ ...
    #define FILE_SHARE_WRITE ...
    #define FILE_SHARE_DELETE ...
    #define FILE_FLAG_BACKUP_SEMANTICS ...
    #define FILE_FLAG_OVERLAPPED ...
    #define FILE_NOTIFY_CHANGE_FILE_NAME ...
    #define FILE_NOTIFY_CHANGE_DIR_NAME ...
    #define FILE_NOTIFY_CHANGE_ATTRIBUTES ...
    #define FILE_NOTIFY_CHANGE_SIZE ...
    #define FILE_NOTIFY_CHANGE_LAST_WRITE ...
    #define FILE_NOTIFY_CHANGE_LAST_ACCESS ...
    #define FILE_NOTIFY_CHANGE_CREATION ...
    #define FILE_NOTIFY_CHANGE_SECURITY ...
    #define FILE_ACTION_ADDED ...
    #define FILE_ACTION_REMOVED ...
    #define FILE_ACTION_MODIFIED ...
    #define FILE_ACTION_RENAMED_OLD_NAME ...
    #define FILE_ACTION_RENAMED_NEW_NAME ...
    #define ERROR_SUCCESS ...
    #define ERROR_OPERATION_ABORTED ...

    typedef struct _FILE_NOTIFY_INFORMATION {
        DWORD NextEntryOffset;
        DWORD Action;
        DWORD FileNameLength;
        WCHAR FileName[1];
    } FILE_NOTIFY_INFORMATION, *PFILE_NOTIFY_INFORMATION;

    typedef struct _OVERLAPPED {
        ULONG_PTR Internal;
        ULONG_PTR InternalHigh;
        union {
            struct {
                DWORD Offset;
                DWORD OffsetHigh;
            };
            PVOID  Pointer;
        };
        HANDLE    hEvent;
    } OVERLAPPED, *LPOVERLAPPED;

    typedef VOID (WINAPI *LPOVERLAPPED_COMPLETION_ROUTINE)(
        DWORD        dwErrorCode,
        DWORD        dwNumberOfBytesTransfered,
        LPOVERLAPPED lpOverlapped
    );

    typedef struct _SECURITY_ATTRIBUTES {
        DWORD  nLength;
        LPVOID lpSecurityDescriptor;
        BOOL   bInheritHandle;
    } SECURITY_ATTRIBUTES, *PSECURITY_ATTRIBUTES, *LPSECURITY_ATTRIBUTES;

    HANDLE WINAPI CreateFile(
        LPCTSTR               lpFileName,
        DWORD                 dwDesiredAccess,
        DWORD                 dwShareMode,
        LPSECURITY_ATTRIBUTES lpSecurityAttributes,
        DWORD                 dwCreationDisposition,
        DWORD                 dwFlagsAndAttributes,
        HANDLE                hTemplateFile
    );
    BOOL WINAPI ReadDirectoryChangesW(
        HANDLE                          hDirectory,
        LPVOID                          lpBuffer,
        DWORD                           nBufferLength,
        BOOL                            bWatchSubtree,
        DWORD                           dwNotifyFilter,
        LPDWORD                         lpBytesReturned,
        LPOVERLAPPED                    lpOverlapped,
        LPOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine
    );
    BOOL WINAPI GetOverlappedResult(
        HANDLE       hFile,
        LPOVERLAPPED lpOverlapped,
        LPDWORD      lpNumberOfBytesTransferred,
        BOOL         bWait
    );
    BOOL WINAPI CancelIoEx(HANDLE hFile, LPOVERLAPPED lpOverlapped);
    BOOL WINAPI CloseHandle(HANDLE hObject);
""")

if __name__ == '__main__':
    ffi.compile()
