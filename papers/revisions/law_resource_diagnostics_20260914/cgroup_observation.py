"""Versioned cgroup-v2 observation diagnostics; never suppress a read failure.

This records the failed operation, errno, path and directory identity. It does
not retroactively explain the historical LA-030 failure or authorize execution.
"""
from __future__ import annotations

import os
import errno
from pathlib import Path
import time


LEAF_FIELDS = ('cpu.stat', 'cpu.max', 'cpuset.cpus.effective', 'memory.current',
               'memory.peak', 'memory.max', 'memory.swap.max', 'memory.events',
               'pids.current', 'pids.max', 'pids.events')
PARENT_FIELDS = ('cpu.stat', 'memory.current', 'memory.peak', 'memory.events',
                 'pids.current', 'pids.events', 'cgroup.events')


def identity(stat):
    return {'device': stat.st_dev, 'inode': stat.st_ino}


def path_identity(path):
    try:
        return {'identity': identity(os.stat(path, follow_symlinks=False))}
    except OSError as exc:
        return {'error_type': type(exc).__name__, 'errno': exc.errno}


class ObservationError(RuntimeError):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(f"{detail['operation']} failed at {detail['path']} "
                         f"({detail['error_type']}, errno={detail.get('errno')})")


class CgroupReader:
    """Pin the sampled directory, rejecting redirection and replacement.

    A pinned directory can outlive a removed kernel cgroup. Any failed file read
    remains a failure; callers must explicitly reconcile it with retained parent
    accounting and their independently observed container termination.
    """
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.resolve() != self.path:
            raise ValueError('An absolute, nonredirected cgroup path is required')
        self.fd = None
        self.initial_identity = None
        try:
            self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.initial_identity = identity(os.fstat(self.fd))
        except OSError as exc:
            try:
                self._raise('open_directory', self.path, exc)
            finally:
                self.close()

    def _raise(self, operation, path, exc):
        detail = {'operation': operation, 'path': str(path),
                  'directory': str(self.path), 'initial_identity': self.initial_identity,
                  'current_path_identity': path_identity(self.path),
                  'error_type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
                  'observed_monotonic': time.monotonic()}
        if self.fd is not None:
            try:
                detail['open_directory_identity'] = identity(os.fstat(self.fd))
            except OSError as fd_error:
                detail['open_directory_error'] = {'error_type': type(fd_error).__name__,
                                                  'errno': fd_error.errno}
        raise ObservationError(detail) from exc

    def read(self, name):
        if name not in set(LEAF_FIELDS) | set(PARENT_FIELDS):
            raise ValueError('Only declared cgroup controller files may be read')
        if self.fd is None:
            raise RuntimeError('Reader is closed')
        path = self.path / name
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.fd)
        except OSError as exc:
            self._raise('open_controller_file', path, exc)
        try:
            try:
                data = os.read(fd, 65537)
                if len(data) > 65536:
                    raise ValueError('Oversized cgroup controller record')
                return data.decode('ascii').strip()
            except OSError as exc:
                self._raise('read_controller_file', path, exc)
        finally:
            os.close(fd)

    def sample(self, *, parent=False):
        before = path_identity(self.path)
        if before.get('identity') != self.initial_identity:
            self._raise('validate_directory_identity', self.path,
                        OSError(errno.ESTALE, 'Directory disappeared or changed identity'))
        fields = {name: self.read(name) for name in (PARENT_FIELDS if parent else LEAF_FIELDS)}
        after = path_identity(self.path)
        if after != before:
            self._raise('revalidate_directory_identity', self.path,
                        OSError(errno.ESTALE, 'Directory identity changed during observation'))
        counters = dict(line.split() for line in fields['cpu.stat'].splitlines())
        fields.update(cpu_usage_seconds=int(counters['usage_usec']) / 1_000_000,
                      observed_monotonic=time.monotonic(), identity=self.initial_identity)
        if parent:
            fields.update(cpu_user_seconds=int(counters['user_usec']) / 1_000_000,
                          cpu_system_seconds=int(counters['system_usec']) / 1_000_000)
        return fields

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def retained_parent_check(previous, current):
    """Necessary parent evidence only; this never admits a failed leaf sample."""
    events = dict(line.split() for line in current['cgroup.events'].splitlines())
    if previous['identity'] != current['identity']:
        raise ValueError('Retained parent identity changed')
    for key in ('cpu_usage_seconds', 'cpu_user_seconds', 'cpu_system_seconds'):
        if current[key] < previous[key]:
            raise ValueError('Retained parent CPU counter regressed')
    if int(current['memory.peak']) < int(previous['memory.peak']):
        raise ValueError('Retained parent memory peak regressed')
    if current['pids.current'] != '0' or events.get('populated') != '0':
        raise ValueError('Retained parent is populated')
    return {'stable_parent': True, 'monotonic_counters': True, 'empty_parent': True,
            'failed_leaf_admitted': False}
