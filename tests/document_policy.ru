模 取 外言 '../src/document.ru'.
状态 取 {'asks':0,'saves':0,'choice':2,'saveOK':假,'writeFail':假}.
次数 取 [0].
作 确认 条件 为 事实, 文 为 句:
    若 非 条件 则 卒 ('FAIL: '+文). 然
    次数[0] 取 次数[0]+1.
    显 'PASS: '+文.
为
算 询问 文档:
    状态 其 增 'asks' ((状态 其 查 'asks')+1).
    得 状态 其 查 'choice'.
法
算 保存 文档:
    状态 其 增 'saves' ((状态 其 查 'saves')+1).
    得 状态 其 查 'saveOK'.
法
算 写入 路, 文, 编码, BOM, 戳:
    若 状态 其 查 'writeFail' 则 卒 'write failed'. 然
    得 'new-stamp'.
法
文档 取 {'path':'old.txt','name':'old.txt','stamp':'old-stamp','encoding':65001,'bom':假,'encodingDirty':假}.
确认 ((模 其 短名 'C:\\文件夹\\a.txt') == 'a.txt') 'Windows Unicode basename'.
确认 ((模 其 短名 '/tmp/a.txt') == 'a.txt') 'slash basename'.
确认 ((模 其 短名 '') == '') 'empty basename'.
确认 (模 其 可以关闭 文档 假 (算 询问) (算 保存)) 'clean close succeeds'.
确认 ((状态 其 查 'asks') == 0) 'clean close does not prompt'.
确认 (非 (模 其 可以关闭 文档 真 (算 询问) (算 保存))) 'Cancel keeps dirty document open'.
确认 ((状态 其 查 'saves') == 0) 'Cancel does not save'.
状态 其 增 'choice' 7.
确认 (模 其 可以关闭 文档 真 (算 询问) (算 保存)) 'Discard authorizes close'.
确认 ((状态 其 查 'saves') == 0) 'Discard does not save'.
状态 其 增 'choice' 6.
确认 (非 (模 其 可以关闭 文档 真 (算 询问) (算 保存))) 'cancelled Save As keeps document open'.
状态 其 增 'saveOK' 真.
确认 (模 其 可以关闭 文档 真 (算 询问) (算 保存)) 'successful save authorizes close'.
状态 其 增 'choice' 0.
确认 (非 (模 其 可以关闭 文档 真 (算 询问) (算 保存))) 'failed dialog never discards'.
模 其 改编码 文档 65001 假.
确认 (非 (模 其 有改 文档 假)) 'same encoding is not a modification'.
模 其 改编码 文档 1200 真.
确认 (模 其 有改 文档 假) 'encoding change is dirty without text edit'.
状态 其 增 'choice' 2.
确认 (非 (模 其 可以关闭 文档 假 (算 询问) (算 保存))) 'encoding-only change prompts and respects Cancel'.
状态 其 增 'writeFail' 真.
失败 取 [假].
试
    模 其 保存文档 文档 'new.txt' 'hello' 'old-stamp' (算 写入).
救 原因
    失败[0] 取 真.
终
确认 失败[0] 'write error propagates'.
确认 ((文档 其 查 'path') == 'old.txt') 'failed save preserves path'.
确认 ((文档 其 查 'stamp') == 'old-stamp') 'failed save preserves conflict stamp'.
确认 (文档 其 查 'encodingDirty') 'failed save preserves dirty state'.
状态 其 增 'writeFail' 假.
模 其 保存文档 文档 'C:\\new.txt' 'hello' 'old-stamp' (算 写入).
确认 ((文档 其 查 'path') == 'C:\\new.txt') 'successful save commits path'.
确认 ((文档 其 查 'name') == 'new.txt') 'successful save commits display name'.
确认 ((文档 其 查 'stamp') == 'new-stamp') 'successful save commits new stamp'.
确认 (非 (文档 其 查 'encodingDirty')) 'successful save clears encoding dirty state'.
显 'TOTAL PASS: '+(次数[0] 为 句).
