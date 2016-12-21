.. image:: https://travis-ci.org/asphalt-framework/asphalt-filewatcher.svg?branch=master
  :target: https://travis-ci.org/asphalt-framework/asphalt-filewatcher
  :alt: Build Status
.. image:: https://coveralls.io/repos/github/asphalt-framework/asphalt-filewatcher/badge.svg?branch=master
  :target: https://coveralls.io/github/asphalt-framework/asphalt-filewatcher?branch=master
  :alt: Code Coverage

This Asphalt framework component provides means for applications to watch files and directories and
receive notifications for changes made to them.

A wide variety of mechanisms are supported:

* inotify_ (Linux)
* ReadDirectoryChangesW_ (Windows)
* FSEvents_ (Mac OS X)
* kqueue_ (*BSD, Mac OS X)
* periodic polling (all platforms)

.. _inotify: https://en.wikipedia.org/wiki/Inotify
.. _ReadDirectoryChangesW: https://msdn.microsoft.com/en-us/library/windows/desktop/aa365465%28v=vs.85%29.aspx
.. _FSEvents: https://en.wikipedia.org/wiki/FSEvents
.. _kqueue: https://developer.apple.com/library/mac/documentation/Darwin/Conceptual/FSEvents_ProgGuide/KernelQueues/KernelQueues.html

Project links
-------------

* `Documentation <http://asphalt-filewatcher.readthedocs.org/en/latest/>`_
* `Help and support <https://github.com/asphalt-framework/asphalt/wiki/Help-and-support>`_
* `Source code <https://github.com/asphalt-framework/asphalt-filewatcher>`_
* `Issue tracker <https://github.com/asphalt-framework/asphalt-filewatcher/issues>`_
