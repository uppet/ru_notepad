"""Retain the original decimal 1 MB fence sample byte-for-byte."""
import hashlib
from windows_ci import gui_markdown_fixture
NAME = 'samples/fence.md'
SIZE = 1000000
SHA256 = '2d9f79ee715b217c00792cf18a67485cdec96a14ea2ac86689156941a022c719'
def validate(data):
    if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError('Original decimal 1,000,000-byte fence sample changed')
    data.decode('utf-8')
    return data
def content():
    return validate(gui_markdown_fixture('unclosed-fence')[0])
def record():
    validate(content())
    return {'name': NAME, 'bytes': SIZE, 'sha256': SHA256,
            'scope': 'original acceptance input retained byte-for-byte; packaging does not claim manual acceptance'}
