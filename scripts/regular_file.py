"""Bounded Linux regular-file reads with descriptor-relative, no-symlink traversal.

No protection against a hostile writer after return; callers must retain pins.
Unsupported no-follow primitives fail closed rather than silently weakening checks.
"""
import os
from pathlib import Path
import stat

MAX_FILE = 16 * 1024 * 1024


def signature(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def read_regular(path, *, limit=MAX_FILE):
    path = Path(path).absolute()
    if '..' in path.parts or not 0 <= limit <= MAX_FILE:
        raise ValueError('unsafe path or file size limit')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    directories = []
    fd = pinned = None
    try:
        parent = os.open(path.anchor, flags | os.O_DIRECTORY)
        directories.append(parent)
        edges = []
        for name in path.parts[1:-1]:
            child = os.open(name, flags | os.O_DIRECTORY, dir_fd=parent)
            edges.append((parent, name, child))
            directories.append(child)
            parent = child
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('ordinary file within size limit required')
        # O_PATH pins the inode without opening a FIFO/device for I/O, even if
        # the directory entry changes after lstat. Reopen only a verified regular
        # inode through the kernel-owned descriptor link, never the mutable path.
        pinned = os.open(path.name, os.O_PATH | os.O_NOFOLLOW, dir_fd=parent)
        opened = os.fstat(pinned)
        if not stat.S_ISREG(opened.st_mode) or signature(before) != signature(opened):
            raise ValueError('file changed before read or is nonregular')
        fd = os.open('/proc/self/fd/' + str(pinned), os.O_RDONLY | os.O_NONBLOCK)
        if signature(os.fstat(fd)) != signature(opened):
            raise ValueError('pinned file changed before read')
        chunks, count = [], 0
        while count <= limit:
            chunk = os.read(fd, min(65536, limit + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
        if count > limit or count != opened.st_size:
            raise ValueError('file exceeded size limit or changed during read')
        if (signature(os.fstat(fd)) != signature(opened) or
                signature(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != signature(opened)):
            raise ValueError('file changed during read')
        for ancestor, name, child in edges:
            actual = os.stat(name, dir_fd=ancestor, follow_symlinks=False)
            held = os.fstat(child)
            if not stat.S_ISDIR(actual.st_mode) or (actual.st_dev, actual.st_ino) != (held.st_dev, held.st_ino):
                raise ValueError('directory changed during read')
        return b''.join(chunks)
    finally:
        if fd is not None:
            os.close(fd)
        if pinned is not None:
            os.close(pinned)
        for directory in reversed(directories):
            os.close(directory)


def artifact_path(root, locator):
    if (not isinstance(locator, str) or Path(locator).is_absolute() or
            '\\' in locator or '://' in locator or
            any(p in ('', '.', '..') for p in locator.split('/'))):
        raise ValueError('unsafe relative artifact locator')
    return Path(root).absolute() / locator
