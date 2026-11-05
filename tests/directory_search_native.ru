# Windows x64 fixture. Stage RuSyntax.dll beside this executable, plus a local
# fixed-drive directory-fixture containing only utf8.txt = UTF8('a😀a').
# Compile with pinned compiler --allow-native and execute on real Windows.
# This is a non-GUI adapter/worker smoke gate, never traversal-security acceptance.
搜 取 外言 '../src/directory_search.ru'.
输 取 外言 '../src/directory_io.ru'.
窗 取 外言 '../src/win32.ru'.
密 取 外言 '如:密'.
_睡 取 (窗 其 内核) 其 绑定 'Sleep' (密 其 签名 (窗 其 V) ([(窗 其 U)]) 'win64').
算 确认 条 名:
    若 非 条 则 卒 名. 然.
    得 空.
法.
算 泵 态:
    循 120000 次
        若 态['status'] != 'running' 则 破. 然.
        搜 其 步进 态.
        确认 (态['lastRawBytes'] <= 4096 且 态['lastWork'] <= 8192 且 态['lastPublished'] <= 16) 'bounded UI tick'.
        _睡 其 调用 [1].
    环.
    确认 (态['status'] != 'running') 'native timeout'.
    循 120000 次
        若 非 (搜 其 维护) 则 破. 然.
        _睡 其 调用 [1].
    环.
    确认 (非 (搜 其 忙)) 'native retirement timeout'.
    得 态.
法.
确认 ((搜 其 初始化) == '') 'helper initialization'.
确认 (搜 其 可用) 'helper available'.
确认 ((输 其 生命周期) == 0) 'no import worker'.
# A PTR HWND must be explicitly reinterpreted, never numerically converted.
零 取 (密 其 指针) 其 值 空. 主 取 (密 其 u64) 其 重释 零.
确认 ((主 其 句) == '0') 'HWND exact reinterpretation'.
显 'PASS: directory initialization and HWND'.
点们 取 输 其 转点 'a😀甲'.
确认 ((点们 其 量) == 3 且 点们[0] == 97 且 点们[1] == 128512 且 点们[2] == 30002) 'owned numeric Unicode conversion'.
确认 ((输 其 文本 点们) == 'a😀甲') 'owned Unicode reconstruction'.
行 取 {'path':'a\n‮','line':1,'column':1,'previewScalars':[10,8238,97],'previewLeadingTruncated':假,'previewMatchTruncated':假}.
确认 ((搜 其 行标签 行) == 'a�� : 1:1 : ��a') 'bounded control and bidi escaping'.
显 'PASS: directory Unicode roundtrip'.
词 取 ''. 循 256 次 词 取 词+'😀'. 环.
程 取 搜 其 检查查询 词. 确认 (程['status'] == 'ok' 且 程['utf8Bytes'] == 1024) 'max Unicode query'.
确认 ((搜 其 检查查询 (词+'a'))['status'] == 'invalid-query') 'query rejects truncation'.
显 'PASS: directory query bounds'.
根 取 (窗 其 目录)+'directory-fixture'.
态 取 搜 其 新建 根 'a'. 泵 态.
确认 (态['status'] == 'complete') 'fixture complete'.
确认 ((态['results'] 其 量) == 2 且 态['filesSearched'] == 1) 'fixture results'.
确认 (态['results'][0]['startUtf8'] == 0 且 态['results'][1]['startUtf8'] == 5) 'UTF8 numeric offsets'.
确认 (态['results'][1]['column'] == 3) 'Unicode scalar column'.
确认 (态['results'][0]['identity'] == 态['results'][1]['identity']) 'opaque exact identity'.
显 'PASS: directory verified results'.
代 取 态['generation'].
循 20 次
    态 取 搜 其 新建 根 'a'. 确认 (态['generation'] > 代) 'monotonic generations'. 代 取 态['generation'].
    搜 其 取消 态. 确认 (态['status'] == 'cancelled') 'immediate cancellation'.
    泵 态. 确认 ((态['results'] 其 量) == 0) 'no late cancellation results'.
环.
显 'PASS: directory repeated cancellation'.
搜 其 关停.
态 取 搜 其 新建 根 'a'. 确认 (态['status'] == 'failed') 'shutdown blocks start'.
显 'PASS: directory shutdown'.
显 'TOTAL PASS: 6'.
