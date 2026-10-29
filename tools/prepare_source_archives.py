#!/usr/bin/env python3
"""Offline-only pinned source archive preparation.

Copy the two pinned, unmodified official ZIPs from third_party/source_archives
to vendor/downloads. No network, extraction, manifest override, or overwrite is
supported. Partial new outputs are retained on failure and never auto-deleted.
A receipt path must be new; its existing parent must be safe. JSON
on stdout is authoritative if the receipt cannot safely be written. The receipt
is reserved with passed=false before any dependency output is created.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import unicodedata
import zipfile
import zlib


@dataclass(frozen=True)
class ArchiveSpec:
    id: str
    filename: str
    bytes: int
    sha256: str
    members: int
    expanded_bytes: int
    folder: str


ARCHIVES = (
    ArchiveSpec('scintilla567', 'scintilla567.zip', 1904249,
                '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c',
                271, 5906269, 'scintilla'),
    ArchiveSpec('lexilla554', 'lexilla554.zip', 1598324,
                '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0',
                1003, 5035224, 'lexilla'),
)
IMPLEMENTATION = 'reconstructed-offline-v1'
CHUNK_BYTES = 65536
MAX_MEMBER_BYTES = 1048576
MAX_RECEIPT_BYTES = 8192
ERROR_CODES = frozenset({
    'in_progress', 'not_checked', 'invalid_arguments', 'unsafe_path',
    'path_missing', 'not_directory', 'link_rejected', 'not_regular',
    'hardlink_rejected', 'path_changed', 'already_exists', 'size_mismatch',
    'hash_mismatch', 'zip_invalid', 'zip_member_count', 'zip_member_path',
    'zip_member_type', 'zip_member_duplicate', 'zip_member_size',
    'zip_expanded_size', 'zip_compression', 'zip_encrypted', 'zip_payload_invalid',
    'io_error', 'internal_error', 'receipt_error', 'source_failed', 'target_failed',
})


class Rejected(Exception):
    def __init__(self, code):
        self.code = code if code in ERROR_CODES else 'internal_error'
        super().__init__(self.code)


def _code(exc):
    if isinstance(exc, Rejected):
        return exc.code
    if isinstance(exc, FileNotFoundError):
        return 'path_missing'
    if isinstance(exc, FileExistsError):
        return 'already_exists'
    if isinstance(exc, OSError):
        return 'io_error'
    return 'internal_error'


def _portable_component(name):
    reserved = {'con', 'prn', 'aux', 'nul'} | {
        base + number for base in ('com', 'lpt') for number in '123456789¹²³'}
    return (bool(name) and name not in ('.', '..') and not name.endswith(('.', ' '))
            and not any(ord(char) < 32 or ord(char) == 127 or char in '/\\<>:"|?*' for char in name)
            and name.split('.')[0].rstrip(' ').casefold() not in reserved)


def _absolute(path):
    path = Path(path)
    # Do not resolve links or normalize away traversal before checking it.
    if '..' in path.parts or '\x00' in str(path):
        raise Rejected('unsafe_path')
    path = Path.cwd() / path if not path.is_absolute() else path
    if os.name == 'nt' and (not path.drive or path.drive.startswith('\\\\')):
        raise Rejected('unsafe_path')
    if any(not _portable_component(part) for part in path.parts[1:]):
        raise Rejected('unsafe_path')
    return path


def _no_link(info):
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise Rejected('link_rejected')


def _directory(info):
    _no_link(info)
    if not stat.S_ISDIR(info.st_mode):
        raise Rejected('not_directory')


def _regular(info):
    _no_link(info)
    if not stat.S_ISREG(info.st_mode):
        raise Rejected('not_regular')
    if info.st_nlink != 1:
        raise Rejected('hardlink_rejected')


def _same(first, second):
    if (first.st_dev, first.st_ino) != (second.st_dev, second.st_ino):
        raise Rejected('path_changed')


def _windows_handle(path, *, directory=False, create=False):
    """Open the final object itself and request read sharing without write/delete.

    Directories request FILE_LIST_DIRECTORY, not attribute-only access (which
    has a share-mode exception). SafeDir retains handles and compares actual
    128-bit FileIdInfo identities. Native rename/reparse/write exclusion tests
    are required on Windows; POSIX unit runs do not prove Windows race behavior.
    """
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create_file = kernel.CreateFileW
    create_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                           wintypes.HANDLE)
    create_file.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = (wintypes.HANDLE,)
    close.restype = wintypes.BOOL
    # FileAttributeTagInfo, FILE_ATTRIBUTE_REPARSE_POINT.
    class AttributeTag(ctypes.Structure):
        _fields_ = [('attributes', wintypes.DWORD), ('tag', wintypes.DWORD)]
    class FileId(ctypes.Structure):
        _fields_ = [('volume', ctypes.c_ulonglong), ('identifier', ctypes.c_ubyte * 16)]
    query = kernel.GetFileInformationByHandleEx
    query.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    query.restype = wintypes.BOOL
    access = 0x81 if directory else (0xC0000000 if create else 0x80000000)
    share = 1
    handle = create_file(str(path), access, share, None, 1 if create else 3,
                         0x00200000 | (0x02000000 if directory else 0), None)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = AttributeTag()
        if not query(handle, 9, ctypes.byref(attributes), ctypes.sizeof(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes.attributes & 0x400:
            raise Rejected('link_rejected')
        if bool(attributes.attributes & 0x10) != directory:
            raise Rejected('not_directory' if directory else 'not_regular')
        identity = FileId()
        if not query(handle, 18, ctypes.byref(identity), ctypes.sizeof(identity)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not any(identity.identifier):
            raise Rejected('io_error')
        return handle, close, (identity.volume, bytes(identity.identifier))
    except BaseException:
        close(handle)
        raise


class SafeDir:
    """Pin and check every directory, including ancestors outside the repo."""
    def __init__(self, path, *, create=False):
        self.path = _absolute(path)
        self.stack = ExitStack()
        self.chain = []
        self.fd = None
        try:
            current = Path(self.path.anchor)
            components = [None, *self.path.parts[1:]]
            parent_fd = None
            for component in components:
                if component is not None:
                    current = current / component
                try:
                    before = (os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
                              if os.name != 'nt' and component is not None else current.lstat())
                except FileNotFoundError:
                    if not create:
                        raise
                    if os.name == 'nt':
                        current.mkdir()
                        before = current.lstat()
                    else:
                        os.mkdir(component, mode=0o700, dir_fd=parent_fd)
                        before = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
                _directory(before)
                if os.name == 'nt':
                    handle, close, identity = _windows_handle(current, directory=True)
                    self.stack.callback(close, handle)
                    opened = current.lstat()
                    _directory(opened)
                    _same(before, opened)
                    self.chain.append((current, identity))
                else:
                    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                    fd = os.open(component if component is not None else str(current),
                                 flags, dir_fd=parent_fd)
                    self.stack.callback(os.close, fd)
                    _directory(os.fstat(fd))
                    _same(before, os.fstat(fd))
                    self.chain.append((parent_fd, component, current, fd))
                    parent_fd = fd
            self.fd = parent_fd
            self.check()
        except BaseException:
            self.stack.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stack.close()

    def check(self):
        for record in self.chain:
            if os.name == 'nt':
                path, identity = record
                after = path.lstat()
                _directory(after)
                handle, close, current_id = _windows_handle(path, directory=True)
                try:
                    if identity != current_id:
                        raise Rejected('path_changed')
                finally:
                    close(handle)
            else:
                parent, name, path, fd = record
                current = (os.stat(name, dir_fd=parent, follow_symlinks=False)
                           if name is not None else path.lstat())
                _directory(current)
                _same(current, os.fstat(fd))

    def info(self, name):
        self.check()
        if not _portable_component(name):
            raise Rejected('unsafe_path')
        return (os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                if os.name != 'nt' else (self.path / name).lstat())

    def open(self, name, *, create=False):
        self.check()
        try:
            before = self.info(name)
        except FileNotFoundError:
            before = None
        if before is not None:
            _regular(before)
            if create:
                raise Rejected('already_exists')
        elif not create:
            raise Rejected('path_missing')
        if os.name == 'nt':
            import msvcrt
            handle, close, _ = _windows_handle(self.path / name, create=create)
            try:
                fd = msvcrt.open_osfhandle(handle, (os.O_RDWR if create else os.O_RDONLY) | os.O_BINARY)
            except BaseException:
                close(handle)
                raise
        else:
            flags = os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_RDWR | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY)
            fd = os.open(name, flags, 0o600, dir_fd=self.fd)
        try:
            self.validate(name, fd)
            if before is not None:
                _same(before, os.fstat(fd))
            return fd
        except BaseException:
            os.close(fd)
            raise

    def validate(self, name, fd):
        opened = os.fstat(fd)
        current = self.info(name)
        _regular(opened)
        _regular(current)
        _same(opened, current)

def _observation():
    return {'actual_bytes': None, 'actual_sha256': None,
            'verified': False, 'error_code': 'not_checked'}


def _report():
    return {'schema_version': 1, 'implementation': IMPLEMENTATION,
            'passed': False, 'error_code': 'in_progress', 'receipt_error_code': None,
            'dependencies': [
                {'id': spec.id, 'expected_bytes': spec.bytes,
                 'expected_sha256': spec.sha256, 'source': _observation(),
                 'target': _observation(), 'status': 'pending'} for spec in ARCHIVES]}


def _member_key(info, spec):
    name = info.orig_filename
    if (name != info.filename or not name or name.startswith('/') or name.endswith('//') or '\\' in name
            or any(ord(char) < 32 or ord(char) == 127 or char in '<>:"|?*' for char in name)):
        raise Rejected('zip_member_path')
    parts = name.rstrip('/').split('/')
    if (parts[0] != spec.folder or len(parts) < 2
            or any(not _portable_component(part) for part in parts)):
        raise Rejected('zip_member_path')
    return '/'.join(unicodedata.normalize('NFC', part).casefold() for part in parts)


def _verify_zip(data, spec):
    if not data.startswith(b'PK\x03\x04'):
        raise Rejected('zip_invalid')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) != spec.members:
                raise Rejected('zip_member_count')
            seen, files, expanded = set(), set(), 0
            for member in members:
                key = _member_key(member, spec)
                if key in seen:
                    raise Rejected('zip_member_duplicate')
                seen.add(key)
                if not member.is_dir():
                    files.add(key)
                mode = stat.S_IFMT(member.external_attr >> 16)
                if (mode not in (0, stat.S_IFDIR if member.is_dir() else stat.S_IFREG)
                        or member.external_attr & 0x400
                        or (member.external_attr & 0x10 and not member.is_dir())):
                    raise Rejected('zip_member_type')
                if member.flag_bits & 0x41:
                    raise Rejected('zip_encrypted')
                if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise Rejected('zip_compression')
                if (not 0 <= member.file_size <= MAX_MEMBER_BYTES
                        or not 0 <= member.compress_size <= spec.bytes
                        or not 0 <= member.header_offset < len(data)
                        or (member.is_dir() and member.file_size != 0)):
                    raise Rejected('zip_member_size')
                expanded += member.file_size
                if expanded > spec.expanded_bytes:
                    raise Rejected('zip_expanded_size')
            if expanded != spec.expanded_bytes:
                raise Rejected('zip_expanded_size')
            for key in seen:
                parts = key.split('/')
                if any('/'.join(parts[:index]) in files for index in range(1, len(parts))):
                    raise Rejected('zip_member_path')
            actual_total = 0
            try:
                for member in members:
                    count, crc = 0, 0
                    with archive.open(member) as stream:
                        while True:
                            chunk = stream.read(min(CHUNK_BYTES, member.file_size - count + 1))
                            if not chunk:
                                break
                            count += len(chunk)
                            crc = zlib.crc32(chunk, crc)
                            actual_total += len(chunk)
                            if count > member.file_size or actual_total > spec.expanded_bytes:
                                raise Rejected('zip_member_size')
                    if count != member.file_size:
                        raise Rejected('zip_member_size')
                    if crc != member.CRC:
                        raise Rejected('zip_payload_invalid')
            except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError, OSError, ValueError, zlib.error):
                raise Rejected('zip_payload_invalid') from None
            if actual_total != spec.expanded_bytes:
                raise Rejected('zip_expanded_size')
    except zipfile.BadZipFile:
        raise Rejected('zip_invalid') from None


def _verify_bytes(data, spec, observation):
    observation['actual_bytes'] = len(data)
    if len(data) != spec.bytes:
        raise Rejected('size_mismatch')
    observation['actual_sha256'] = hashlib.sha256(data).hexdigest()
    if observation['actual_sha256'] != spec.sha256:
        raise Rejected('hash_mismatch')
    _verify_zip(data, spec)
    observation.update(verified=True, error_code=None)


def _read_verified(directory, spec, observation):
    fd = directory.open(spec.filename)
    try:
        before = os.fstat(fd)
        observation['actual_bytes'] = before.st_size
        if before.st_size != spec.bytes:
            raise Rejected('size_mismatch')
        chunks, count = [], 0
        while count <= spec.bytes:
            chunk = os.read(fd, min(CHUNK_BYTES, spec.bytes + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
        directory.validate(spec.filename, fd)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise Rejected('path_changed')
        data = b''.join(chunks)
        _verify_bytes(data, spec, observation)
        return data
    finally:
        os.close(fd)


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise Rejected('io_error')
        view = view[count:]


def _copy_exclusive(directory, spec, data):
    fd = directory.open(spec.filename, create=True)
    try:
        _write_all(fd, data)
        os.fsync(fd)
        directory.validate(spec.filename, fd)
    finally:
        os.close(fd)


def _run(root, report):
    root = _absolute(root)
    with SafeDir(root / 'third_party' / 'source_archives') as source:
        payloads = []
        for spec, item in zip(ARCHIVES, report['dependencies']):
            try:
                payloads.append(_read_verified(source, spec, item['source']))
            except Exception as exc:
                item['source'].update(verified=False, error_code=_code(exc))
                item['status'] = 'failed'
                payloads.append(None)
        if any(payload is None for payload in payloads):
            raise Rejected('source_failed')
        with SafeDir(root / 'vendor' / 'downloads', create=True) as target:
            missing = []
            for spec, item in zip(ARCHIVES, report['dependencies']):
                try:
                    target.info(spec.filename)
                except FileNotFoundError:
                    missing.append(True)
                    continue
                missing.append(False)
                try:
                    _read_verified(target, spec, item['target'])
                    item['status'] = 'reused'
                except Exception as exc:
                    item['target'].update(verified=False, error_code=_code(exc))
                    item['status'] = 'failed'
            if any(item['status'] == 'failed' for item in report['dependencies']):
                raise Rejected('target_failed')
            for spec, item, data, absent in zip(ARCHIVES, report['dependencies'], payloads, missing):
                if absent:
                    try:
                        _copy_exclusive(target, spec, data)
                        item['status'] = 'copied'
                    except Exception as exc:
                        item['target'].update(verified=False, error_code=_code(exc))
                        item['status'] = 'failed'
                        raise Rejected('target_failed') from None
            # Success requires fresh full validation of BOTH source and target.
            for directory, side in ((source, 'source'), (target, 'target')):
                for spec, item in zip(ARCHIVES, report['dependencies']):
                    item[side] = _observation()
                    try:
                        _read_verified(directory, spec, item[side])
                    except Exception as exc:
                        item[side].update(verified=False, error_code=_code(exc))
                        item['status'] = 'failed'
            if any(item['status'] == 'failed' for item in report['dependencies']):
                if any(not item['source']['verified'] for item in report['dependencies']):
                    raise Rejected('source_failed')
                raise Rejected('target_failed')
            source.check()
            target.check()
    report.update(passed=True, error_code=None)


def _receipt_bytes(report):
    data = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')
    if len(data) > MAX_RECEIPT_BYTES:
        raise Rejected('receipt_error')
    return data


def _write_receipt(directory, name, fd, report):
    directory.validate(name, fd)
    data = _receipt_bytes(report)
    os.lseek(fd, 0, os.SEEK_SET)
    _write_all(fd, data)
    os.ftruncate(fd, len(data))
    os.fsync(fd)
    directory.validate(name, fd)


def prepare(root, receipt):
    """Return a bounded JSON-safe report; failure never propagates path text.

    The receipt is an exclusively created regular file in an already existing,
    non-linked parent directory. Reusing a receipt path is deliberately rejected.
    Callers must use a new receipt path for each attempt, including reuse checks.
    """
    report = _report()
    try:
        receipt = _absolute(receipt)
        with SafeDir(receipt.parent) as directory:
            fd = directory.open(receipt.name, create=True)
            try:
                try:
                    _write_receipt(directory, receipt.name, fd, report)
                    try:
                        _run(root, report)
                    except Exception as exc:
                        report.update(passed=False, error_code=_code(exc))
                    _write_receipt(directory, receipt.name, fd, report)
                except Exception as exc:
                    report.update(passed=False, error_code='receipt_error', receipt_error_code=_code(exc))
                    # A failed fsync may occur after success bytes were written.
                    # Clear those bytes only through the still-owned safe fd.
                    # If storage is unusable, stdout/exit status remain failure.
                    try:
                        _write_receipt(directory, receipt.name, fd, report)
                    except Exception:
                        pass
            finally:
                os.close(fd)
    except Exception as exc:
        report.update(passed=False, error_code='receipt_error', receipt_error_code=_code(exc))
    return report


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        report = _report()
        report['error_code'] = 'invalid_arguments'
        print(_receipt_bytes(report).decode('ascii'), end='')
        raise SystemExit(2)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args(argv)
    report = prepare(args.root, args.receipt)
    print(_receipt_bytes(report).decode('ascii'), end='')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
