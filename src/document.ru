# Portable application state policy. No OS, FFI, file writes or editor widget.
本地 取 外言 'i18n.ru'.
算 短名 路 为 句:
    位 取 路 其 量.
    循
        若 位 <= 0 则 破. 然
        位 取 位-1.
        若 路[位] == '\\' 或 路[位] == '/' 则 得 路[位+1:]. 然
    环
    得 路.
法
算 编码名 编码:
    若 编码 == 65001 则 得 'UTF-8'. 然
    若 编码 == 1200 则 得 'UTF-16 LE'. 然
    若 编码 == 1201 则 得 'UTF-16 BE'. 然
    若 编码 == 1252 则 得 'Windows-1252'. 然
    若 编码 == 936 则 得 'GBK (CP936)'. 然
    得 'CP'+(编码 为 句).
法
算 有改 文档, 文本改 为 事实:
    得 文本改 或 (文档 其 查 'encodingDirty').
法
算 改编码 文档, 编码 为 数, BOM 为 事实:
    若 编码 != 65001 且 编码 != 1200 且 编码 != 1201 且 编码 != 1252 且 编码 != 936 则 卒 (本地 其 文本 'error.document.unsupported_encoding'). 然
    若 BOM 且 (编码 == 1252 或 编码 == 936) 则 卒 (本地 其 文本 'error.document.legacy_bom'). 然
    若 编码 != (文档 其 查 'encoding') 或 BOM != (文档 其 查 'bom') 则
        文档 其 增 'encoding' 编码.
        文档 其 增 'bom' BOM.
        文档 其 增 'encodingDirty' 真.
    然
    得 空.
法
算 保存文档 文档, 路 为 句, 文 为 句, 戳 为 句, 写入 为 算:
    # The write callback must finish successfully before any clean-state commit.
    新戳 取 写入 路 文 (文档 其 查 'encoding') (文档 其 查 'bom') 戳.
    文档 其 增 'path' 路.
    文档 其 增 'name' (短名 路).
    文档 其 增 'stamp' 新戳.
    文档 其 增 'encodingDirty' 假.
    得 新戳.
法
算 可以关闭 文档, 文本改 为 事实, 询问 为 算, 保存 为 算:
    若 非 (有改 文档 文本改) 则 得 真. 然
    选择 取 询问 文档.
    若 选择 == 6 则 得 保存 文档. 然
    若 选择 == 7 则 得 真. 然
    # Includes explicit Cancel, dialog failure, and unexpected results.
    得 假.
法
