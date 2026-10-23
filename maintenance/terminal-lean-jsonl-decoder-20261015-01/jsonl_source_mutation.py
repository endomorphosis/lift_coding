"""Bounded corruption and actual current-source exit controls for an owned run.

Only this successor's copied source is temporarily changed. The native owner
and structural callback perform their real entry/exit observations; no database
head is forged or reset. The source is restored in finally before any positive
fault report is published. This module never executes the repository source.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import resource
import stat

from jsonl_io import ROOT, FALSE, inputs, read, write, wire, sha

SCHEMA = "terminal-jsonl-model-source-mutation@1"
SOURCE_PATH = "headless-terminal/environment/base_terminal.py"
MAX_SOURCE_BYTES = 8192
MUTATION = b"\n# Authored current-source exit fault; never executed.\n"


class PackingFaultError(ValueError):
    """A requested fault was not refused or exact restoration failed."""


def _need(value, message):
    if not value:
        raise PackingFaultError(message)


class _OwnedSourceMutation:
    def __init__(self, path, original):
        self.path, self.original, self.applied = Path(path), original, False
        _need(type(original) is bytes and 0 < len(original) and len(original) + len(MUTATION) <= MAX_SOURCE_BYTES,
              "bounded exact original source required")
        _need(self.path.is_absolute() and self.path.resolve(strict=True) == self.path and ROOT in self.path.parents,
              "only a canonical copied successor source may be changed")
        self.descriptor = os.open(self.path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            self.before = os.fstat(self.descriptor)
            _need(stat.S_ISREG(self.before.st_mode) and self.before.st_nlink == 1 and
                  self.before.st_size == len(original), "single-link regular copied source required")
            actual = os.read(self.descriptor, MAX_SOURCE_BYTES + 1)
            _need(actual == original, "copied source differs before fault")
        except BaseException:
            os.close(self.descriptor)
            raise

    def _identity(self):
        actual, named = os.fstat(self.descriptor), self.path.lstat()
        _need(actual.st_dev == named.st_dev == self.before.st_dev and
              actual.st_ino == named.st_ino == self.before.st_ino and
              actual.st_nlink == named.st_nlink == 1 and stat.S_ISREG(named.st_mode),
              "owned source locator changed during fault")

    def _replace_bytes(self, raw):
        self._identity()
        os.lseek(self.descriptor, 0, os.SEEK_SET)
        offset = 0
        while offset < len(raw):
            written = os.write(self.descriptor, raw[offset:])
            _need(written > 0, "copied source write failed")
            offset += written
        os.ftruncate(self.descriptor, len(raw))
        os.fsync(self.descriptor)

    def apply(self):
        _need(not self.applied, "one bounded source mutation per control required")
        # Mark first so a partial write still invokes exact restoration.
        self.applied = True
        self._replace_bytes(self.original + MUTATION)

    def close(self):
        try:
            if self.applied:
                self._replace_bytes(self.original)
                os.utime(self.descriptor, ns=(self.before.st_atime_ns, self.before.st_mtime_ns))
                self._identity()
                os.lseek(self.descriptor, 0, os.SEEK_SET)
                _need(os.read(self.descriptor, MAX_SOURCE_BYTES + 1) == self.original,
                      "exact original copied source was not restored")
        finally:
            os.close(self.descriptor)


@contextmanager
def owned_source_mutation(path, original):
    """Keep mutation alive across callback exit; restore on every exception."""
    mutation = _OwnedSourceMutation(path, original)
    try:
        yield mutation
    finally:
        mutation.close()


