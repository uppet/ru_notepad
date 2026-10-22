#!/usr/bin/env python3
"""Explicit opt-in acquisition; never starts the downloaded program."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
import shutil
import stat
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

VERSION = 'v8.9.8.1'
BASE = f'https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/{VERSION}/'
PINS = {
    'npp.8.9.8.1.portable.x64.zip': (8250001, 'beddf5548e75c97930d1575ba1c7d113e6e2b33d0a200310e734ca08e225f414'),
    'npp.8.9.8.1.checksums.sha256': (1271, '78bc138eff0675589b7887ed3114d30acdcd807f19f36b3ba4095b44173d1e36'),
}
MAX_TOTAL = 100 * 1024 * 1024
MAX_MEMBER = 25 * 1024 * 1024
MAX_ENTRIES = 5000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, size, sha256):
    if len(data) != size or digest(data) != sha256:
        raise ValueError('asset_digest_or_size_mismatch')


def verify_checksums(data, filename, expected):
    lines = data.decode('ascii').splitlines()
    matches = []
    for line in lines:
        match = re.fullmatch(r'([0-9a-fA-F]{64}) [ *](.+)', line)
        if match and match[2] == filename:
            matches.append(match[1].lower())
    if matches != [expected]:
        raise ValueError('checksum_entry_missing_duplicate_or_mismatch')


def trusted_url(url):
    p = urllib.parse.urlsplit(url)
    return (p.scheme == 'https' and p.hostname in
            {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
            and not p.username and not p.password and p.port in (None, 443))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not trusted_url(newurl):
            raise ValueError('untrusted_download_redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, size, sha256):
    if not trusted_url(url) or size > 20 * 1024 * 1024:
        raise ValueError('invalid_download_request')
    opener = urllib.request.build_opener(SafeRedirect())
    with opener.open(urllib.request.Request(url, headers={'User-Agent': 'npp-comparison-pinned/1'}), timeout=60) as response:
        if not trusted_url(response.url):
            raise ValueError('untrusted_download_response')
        data = response.read(size + 1)
    verify(data, size, sha256)
    return data


def safe_members(archive):
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ValueError('archive_entry_limit')
    total, names = 0, set()
    for entry in infos:
        name = entry.filename
        parts = PurePosixPath(name).parts
        if (not name or '\\' in name or ':' in name or '\x00' in name or name.startswith('/')
                or any(p in ('.', '..') or p.endswith((' ', '.')) or
                       p.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}
                       for p in name.rstrip('/').split('/'))):
            raise ValueError('unsafe_archive_path')
        folded = name.rstrip('/').casefold()
        if folded in names:
            raise ValueError('duplicate_archive_path')
        names.add(folded)
        mode = entry.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or entry.external_attr & 0x400 or entry.flag_bits & 1:
            raise ValueError('archive_link_special_reparse_or_encrypted')
        if entry.is_dir() and kind == stat.S_IFREG:
            raise ValueError('inconsistent_archive_kind')
        total += entry.file_size
        if (entry.file_size > MAX_MEMBER or total > MAX_TOTAL or
                entry.file_size > max(1, entry.compress_size) * 1000):
            raise ValueError('archive_expansion_limit')
    # Reject file/directory aliases independent of member ordering.
    files = {e.filename.casefold() for e in infos if not e.is_dir()}
    for entry in infos:
        if any('/'.join(entry.filename.casefold().split('/')[:i]) in files
               for i in range(1, len(entry.filename.rstrip('/').split('/')))):
            raise ValueError('archive_parent_is_file')
    return infos


def extract(data, destination):
    destination = Path(destination)
    # Caller supplies an owned, existing parent; do not follow symlink parents.
    if any(p.is_symlink() or (p.exists() and getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
           for p in (destination, *destination.parents)):
        raise ValueError('symlink_destination')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = safe_members(archive)
        destination.mkdir(exist_ok=False)
        try:
            for entry in entries:
                target = destination.joinpath(*PurePosixPath(entry.filename).parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, length=65536)
                if target.stat().st_size != entry.file_size:
                    raise ValueError('archive_member_size_mismatch')
            exe = destination / 'notepad++.exe'
            if not exe.is_file():
                raise ValueError('missing_root_executable')
            for name in ('doLocalConf.xml', 'disableNppAutoUpdate.xml'):
                marker = destination / name
                if marker.exists():
                    if not marker.is_file() or marker.stat().st_size:
                        raise ValueError('unexpected_existing_config_marker')
                else:
                    marker.touch(exist_ok=False)
            return {'executable_sha256': digest(exe.read_bytes()), 'file_count': sum(p.is_file() for p in destination.rglob('*')),
                    'archive_sha256': digest(data), 'executed': False,
                    'files': {p.relative_to(destination).as_posix(): digest(p.read_bytes())
                              for p in sorted(destination.rglob('*')) if p.is_file()}}
        except BaseException:
            # Only the directory exclusively created above belongs to this call.
            shutil.rmtree(destination)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-download', action='store_true', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name('release-lock.json').read_text())
    if lock['version'] != VERSION or lock['prerelease'] or len(lock['assets']) != len(PINS):
        raise ValueError('release_lock_mismatch')
    for asset in lock['assets']:
        if asset['name'] not in PINS or (asset['bytes'], asset['sha256']) != PINS[asset['name']] or asset['url'] != BASE + asset['name']:
            raise ValueError('release_lock_asset_mismatch')
    if args.destination.exists() or not args.destination.parent.is_dir():
        raise ValueError('destination_must_be_new_with_existing_parent')
    acquired = {name: download(BASE + name, size, sha) for name, (size, sha) in PINS.items()}
    filename = 'npp.8.9.8.1.portable.x64.zip'
    verify_checksums(acquired['npp.8.9.8.1.checksums.sha256'], filename, PINS[filename][1])
    print(json.dumps(extract(acquired[filename], args.destination), sort_keys=True))


if __name__ == '__main__':
    try:
        result = main()
    except Exception:
        import sys
        print('COMPARISON_FAILURE_CODE=1', file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(result or 0)
