# Windows ACL integration harness helper; only use with synthetic test files.
文件库 取 外言 '../src/file_codec.ru'.
本地 取 外言 '../src/i18n.ru'.
算 元初 外参 为 句 阵:
    若 外参 其 量 != 2 则
        显 'Usage: file_codec_security_probe.exe TEST_FILE save|expect-replace-failure'.
        得 2.
    然
    模式 取 外参[1].
    若 模式 != 'save' 且 模式 != 'expect-replace-failure' 则 得 2. 然
    文档 取 文件库 其 读文件 外参[0] 0.
    试
        文件库 其 写文件 文档['path'] 'synthetic replacement\r\n' 65001 假 文档['stamp'].
    救 原因
        显 原因.
        若 模式 == 'expect-replace-failure' 且 原因 其 含 (本地 其 文本 'error.file.replace_recovery') 则
            显 'EXPECTED_REPLACE_FAILURE'.
            得 0.
        然
        得 1.
    终
    若 模式 == 'expect-replace-failure' 则
        显 'FAIL: replacement unexpectedly succeeded'.
        得 1.
    然
    显 'SAVE_PASS'.
    得 0.
法
