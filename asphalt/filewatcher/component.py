import logging
import platform
import select
from functools import partial
from pathlib import Path
from typing import Dict, Any, Union, Iterable

from asphalt.core import Component, Context, merge_config, qualified_name, PluginContainer
from typeguard import check_argument_types

from asphalt.filewatcher.api import FileEventType

logger = logging.getLogger(__name__)
watchers = PluginContainer('asphalt.watcher.watchers')

if platform.system() == 'Linux':
    default_backend = 'inotify'
elif platform.system() == 'Windows':
    default_backend = 'windows'
elif hasattr(select, 'kqueue'):
    default_backend = 'kqueue'
else:
    default_backend = 'poll'


def create_watcher(path: Union[str, Path], events: Union[str, Iterable[FileEventType]], *,
                   recursive: bool = True, backend: str = None, **kwargs):
    """
    Create a new file system watcher.

    If no backend name is explicitly given, the best default backend for the current platform is
    used.

    :param path: path to the directory to watch
    :param events: either a comma separated string or iterable of event types to watch
    :param recursive: ``True`` to watch for changes in subdirectories as well
    :param backend: name of the backend plugin (from the ``asphalt.watcher.watchers`` namespace)

    """
    assert check_argument_types()
    if isinstance(events, str):
        events = [getattr(FileEventType, name.strip()) for name in events.split(',')]

    watcher_class = watchers.resolve(backend or default_backend)
    return watcher_class(path, events=set(events), recursive=recursive, **kwargs)


class FileWatcherComponent(Component):
    """
    Publishes one or more :class:`~asphalt.filewatcher.api.FileWatcher` resources.

    If more than one watcher is to be configured, provide a ``watchers`` argument as a dictionary
    where the key is the resource name and the value is a dictionary of keyword arguments to
    :meth:`create_watcher`. Otherwise, directly pass those keyword arguments to the component
    constructor itself.

    If ``watchers`` is defined, any extra keyword arguments are used as default values for
    :meth:`create_watcher` for all watchers (:func:`~asphalt.core.util.merge_config` is used to
    merge the per-watcher arguments with the defaults). Otherwise, a single watcher is created
    based on the provided default arguments, with ``context_attr`` defaulting to ``watcher``.

    :param watchers: a dictionary of resource name ⭢ :func:`create_watcher` keyword arguments
    :param default_watcher_args: default values for omitted :func:create_watcher` arguments
    """

    def __init__(self, watchers: Dict[str, Dict[str, Any]] = None, **default_watcher_args):
        assert check_argument_types()
        watchers = watchers or {}
        if default_watcher_args:
            default_watcher_args.setdefault('context_attr', 'watcher')
            watchers['default'] = default_watcher_args

        self.watchers = []
        for resource_name, config in watchers.items():
            config = merge_config(default_watcher_args, config)
            context_attr = config.pop('context_attr', resource_name)
            watcher = create_watcher(**config)
            self.watchers.append((resource_name, context_attr, watcher))

    @staticmethod
    async def shutdown(event, watcher, resource_name):
        watcher.stop()
        logger.info('File system watcher (%s) shut down', resource_name)

    async def start(self, ctx: Context):
        for resource_name, context_attr, watcher in self.watchers:
            await watcher.start(ctx)
            ctx.publish_resource(watcher, resource_name, context_attr)
            ctx.finished.connect(
                partial(self.shutdown, watcher=watcher, resource_name=resource_name))
            logger.info('Configured file system watcher (%s / ctx.%s; class=%s)', resource_name,
                        context_attr, qualified_name(watcher))
