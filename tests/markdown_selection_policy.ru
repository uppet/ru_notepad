# Exact production extension and label policy; no Win32 or native substitutes.
策 取 外言 '../src/syntax_policy.ru'.
次数 取 [0].
作 确认 条件 为 事实 名 为 句:
    若 非 条件 则 卒 'FAIL: '+名. 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+名.
为
例们 取 [
    ['notes.md','markdown'],['NOTES.MD','markdown'],['notes.mD','markdown'],
    ['notes.markdown','markdown'],['NOTES.MARKDOWN','markdown'],['notes.MarkDown','markdown'],
    ['.md','markdown'],['.markdown','markdown'],['甲😀.mArKdOwN','markdown'],
    ['C:/甲/notes.md','markdown'],['C:\\甲\\notes.MARKDOWN','markdown'],
    ['\\\\server\\share\\notes.md','markdown'],
    ['README','plain'],['notes.mdx','plain'],['notes.md.bak','plain'],
    ['notes.markdowns','plain'],['notes.markdown ','plain'],['notes.md\n','plain'],
    ['notes.ＭＤ','plain'],['notes.md/','plain'],['notes.markdown\\','plain'],
    ['C:/folder.md/README','plain'],['C:\\folder.markdown\\README','plain'],
    ['C:/folder.md/a.cpp','cpp'],['C:/folder.markdown/a.json','json'],
    ['C:/folder.markdown/a.ru','ru'],['notes.md.txt','plain'],['','plain']
].
位 取 0.
循 例们 其 量 次
    项 取 例们[位].
    确认 ((策 其 识别 项[0]) == 项[1]) ('Markdown path case '+(位 为 句)).
    位 取 位+1.
环
确认 ((策 其 名称 'markdown') == 'Markdown') 'Markdown label'.
确认 ((策 其 名称 'Markdown') == 'Plain text') 'language IDs remain exact'.
确认 ((策 其 名称 'plain') == 'Plain text') 'manual Plain label remains available'.
显 'TOTAL PASS: '+(次数[0] 为 句).
