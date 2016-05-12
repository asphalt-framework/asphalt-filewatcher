from cffi import FFI

ffi = FFI()
ffi.set_source('asphalt.filewatcher.watchers._inotify', '#include <sys/inotify.h>')
ffi.cdef("""
    struct inotify_event {
        int      wd;       /* Watch descriptor */
        uint32_t mask;     /* Mask describing event */
        uint32_t cookie;   /* Unique cookie associating related events (for rename(2)) */
        uint32_t len;      /* Size of name field */
        char     name[];   /* Optional null-terminated name */
    };
    int inotify_init1(int flags);
    int inotify_add_watch(int fd, const char *pathname, uint32_t mask);
    int inotify_rm_watch(int fd, int wd);

    #define IN_ACCESS ...
    #define IN_ATTRIB ...
    #define IN_CREATE ...
    #define IN_DELETE ...
    #define IN_DELETE_SELF ...
    #define IN_MODIFY ...
    #define IN_MOVED_FROM ...
    #define IN_MOVED_TO ...
""")

if __name__ == '__main__':
    ffi.compile()
