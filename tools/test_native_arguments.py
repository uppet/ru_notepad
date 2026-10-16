#!/usr/bin/env python3
"""Execute parser/gate mutants, not Win32 operations or general type inference."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ru-root', type=Path, required=True)
    args = parser.parse_args()
    native = "密 取 外言 '如:密'.\n库 取 密 其 系统库 'kernel32.dll'.\n函数 取 库 其 绑定 'example' (密 其 签名 (密 其 i32) ([(密 其 i32)]) 'win64').\n"
    cases = [
        ('grouped bit field', '值 取 (属性 其 位段 4 1) == 1.', False),
        ('original swallowed comparison', '若 属性 其 位段 4 1 == 1 则 显 1. 然', True),
        ('explicit fact width', '值 取 属性 其 位段 4 真.', True),
        ('fact start position', '值 取 属性 其 位段 (非 真) 1.', True),
        ('wrong bit-field arity', '值 取 属性 其 位段 4.', True),
        ('native numeric literal', native + '函数 其 调用 [1].', False),
        ('native literal fact', native + '函数 其 调用 [真].', True),
        ('native swallowed comparison', native + '函数 其 调用 [1 == 1].', True),
    ]
    with tempfile.TemporaryDirectory(prefix='ru-notepad-argument-audit-') as folder:
        root = Path(folder)
        (root / 'src').mkdir()
        for name, source, rejected in cases:
            (root / 'src' / 'mutant.ru').write_text(source, encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'tools/check_native_arguments.py'),
                '--ru-root', str(args.ru_root.resolve()), '--root', str(root)],
                capture_output=True, text=True)
            report = json.loads(result.stdout)
            errors = report['member_mismatches'] + report['known_type_mismatches']
            if result.returncode != int(rejected) or bool(errors) != rejected or report['unresolved']:
                raise RuntimeError(f'{name}: unexpected audit result: {result.stdout}\n{result.stderr}')
            print('PASS: ' + name)
    print(f'TOTAL STATIC AUDIT PASS: {len(cases)}')


if __name__ == '__main__':
    main()
