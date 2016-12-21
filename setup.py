import platform
from pathlib import Path

from setuptools import setup

cffi_modules = []
if platform.system() == 'Linux':
    cffi_modules = ['asphalt/filewatcher/watchers/inotify_build.py:ffi']
elif platform.system() == 'Windows':
    cffi_modules = ['asphalt/filewatcher/watchers/windows_build.py:ffi']

setup(
    name='asphalt-filewatcher',
    use_scm_version={
        'version_scheme': 'post-release',
        'local_scheme': 'dirty-tag'
    },
    description='File change notifier component for the Asphalt framework',
    long_description=Path(__file__).with_name('README.rst').read_text('utf-8'),
    author='Alex Grönholm',
    author_email='alex.gronholm@nextday.fi',
    url='https://github.com/asphalt-framework/asphalt-filewatcher',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],
    license='Apache License 2.0',
    zip_safe=False,
    packages=[
        'asphalt.filewatcher',
        'asphalt.filewatcher.watchers'
    ],
    cffi_modules=cffi_modules,
    setup_requires=[
        'setuptools_scm >= 1.7.0',
        'cffi >= 1.8.1; platform_system == "Linux" or platform_system == "Windows"'
    ],
    install_requires=[
        'asphalt ~= 2.0',
        'cffi >= 1.8.1; platform_system == "Linux" or platform_system == "Windows"'
    ],
    entry_points={
        'asphalt.components': [
            'filewatcher = asphalt.filewatcher.component:FileWatcherComponent'
        ],
        'asphalt.watcher.watchers': [
            'inotify = asphalt.filewatcher.watchers.inotify:INotifyFileWatcher',
            'kqueue = asphalt.filewatcher.watchers.kqueue:KQueueFileWatcher',
            'poll = asphalt.filewatcher.watchers.poll:PollingFileWatcher',
            'windows = asphalt.filewatcher.watchers.windows:WindowsFileWatcher'
        ]
    }
)
