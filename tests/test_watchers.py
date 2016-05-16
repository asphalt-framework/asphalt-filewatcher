import platform
import stat
from asyncio import Queue, wait_for
from asyncio.tasks import Task, wait
from pathlib import Path

import pytest

from asphalt.filewatcher.api import FileEventType, FileWatcher
from asphalt.filewatcher.component import create_watcher


@pytest.fixture
def testdir(tmpdir):
    tmpdir.join('testfile').write_binary(b'Hello')
    tmpdir.mkdir('subdir').join('testfile2').write_binary(b'Hello')
    return Path(str(tmpdir))


@pytest.fixture
def tmpdir2(tmpdir_factory):
    path = tmpdir_factory.mktemp('tmpdir2')
    return Path(str(path))


@pytest.fixture
def event_queue(watcher: FileWatcher):
    queue = Queue()
    watcher.accessed.connect(queue.put)
    watcher.attribute_changed.connect(queue.put)
    watcher.created.connect(queue.put)
    watcher.deleted.connect(queue.put)
    watcher.modified.connect(queue.put)
    return queue


@pytest.fixture(params=['inotify', 'windows', 'poll'])
def watcher_type(request):
    return request.param


@pytest.yield_fixture
def watcher(request, testdir, watcher_type, event_loop):
    events = getattr(request, 'param', FileEventType.all)
    kwargs = {'interval': 0.2} if watcher_type == 'poll' else {}

    try:
        watcher = create_watcher(testdir, events=events, recursive=True, backend=watcher_type,
                                 **kwargs)
    except ImportError:
        return pytest.skip('The "%s" watcher is not available on this platform' % watcher_type)

    watcher.start()
    yield watcher
    watcher.stop()

    # Finish any leftover tasks
    all_tasks = Task.all_tasks(event_loop)
    if all_tasks:
        event_loop.run_until_complete(wait(all_tasks))


@pytest.mark.skipif(platform.system() == 'Windows',
                    reason='last access timestamps are disabled since Windows 7')
@pytest.mark.parametrize('watcher', [{FileEventType.access}], indirect=['watcher'])
@pytest.mark.asyncio
async def test_access(event_queue: Queue, testdir: Path):
    testdir.joinpath('testfile').read_bytes()
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'accessed'
    assert event.path == Path('testfile')


@pytest.mark.asyncio
async def test_attribute_change(event_queue: Queue, testdir: Path, watcher_type):
    if watcher_type == 'windows':
        pytest.skip('cannot distinguish attribute changes from file writes with '
                    'ReadDirectoryChangesW')

    testdir.joinpath('testfile').chmod(stat.S_IREAD)
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'attribute_changed'
    assert event.path == Path('testfile')


@pytest.mark.asyncio
async def test_create(event_queue: Queue, testdir: Path):
    testdir.joinpath('test.dat').write_bytes(b'Hello')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'created'
    assert event.path == Path('test.dat')


@pytest.mark.asyncio
async def test_delete(event_queue: Queue, testdir: Path):
    testdir.joinpath('testfile').unlink()
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'deleted'
    assert event.path == Path('testfile')


@pytest.mark.asyncio
async def test_modify(event_queue: Queue, testdir: Path):
    testdir.joinpath('testfile').write_bytes(b'World')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'modified'
    assert event.path == Path('testfile')


@pytest.mark.asyncio
async def test_moved_to(event_queue: Queue, testdir: Path, tmpdir2: Path):
    otherfile = tmpdir2 / 'otherfile'
    otherfile.write_bytes(b'Hello')
    otherfile.rename(testdir / 'otherfile')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'created'
    assert event.path == Path('otherfile')


@pytest.mark.asyncio
async def test_moved_from(event_queue: Queue, testdir: Path, tmpdir2: Path):
    testdir.joinpath('testfile').rename(tmpdir2 / 'testfile')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'deleted'
    assert event.path == Path('testfile')


@pytest.mark.asyncio
async def test_directory_moved_from(event_queue: Queue, testdir: Path, tmpdir2: Path):
    """
    Test that once a subdirectory has been moved out of the tree, it no longer generates
    events.

    """
    testdir.joinpath('subdir').rename(tmpdir2 / 'subdir')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'deleted'
    assert event.path == Path('subdir')


@pytest.mark.parametrize('watcher', [{FileEventType.delete}], indirect=['watcher'])
@pytest.mark.asyncio
async def test_existing_subdir_delete(event_queue: Queue, testdir: Path):
    """Test that delete notifications from existing subdirectories work."""
    testdir.joinpath('subdir', 'testfile2').unlink()
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'deleted'
    assert event.path == Path('subdir', 'testfile2')


@pytest.mark.parametrize('watcher', [{FileEventType.create}], indirect=['watcher'])
@pytest.mark.asyncio
async def test_existing_subdir_create(event_queue: Queue, testdir: Path, watcher):
    """Test that create notifications from existing subdirectories work."""
    testdir.joinpath('subdir', 'test.dat').write_bytes(b'Hello')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'created'
    assert event.path == Path('subdir', 'test.dat')


@pytest.mark.parametrize('watcher', [{FileEventType.create, FileEventType.delete}],
                         indirect=['watcher'])
@pytest.mark.asyncio
async def test_new_subdir(event_queue: Queue, testdir: Path):
    """Test that change notifications from existing subdirectories work."""
    subdir = testdir / 'newsubdir'
    subdir.mkdir()
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'created'
    assert event.path == Path('newsubdir')

    subdir.joinpath('test.dat').write_bytes(b'Hello')
    event = await wait_for(event_queue.get(), 2)
    assert event.topic == 'created'
    assert event.path == Path('newsubdir', 'test.dat')
