# Markdown 增量扫描候选（wij）

本分支基于 `wip@d964ea9f7e27065aa5bbcced8d6c7526a6224dd1`，提交此前在如言 `bs` 分支上验证的 Markdown 密核与增量检查点候选，供 `wip` 开发者 review。首次打开仍全量扫描；上一修订完成后，无增减行的单次编辑可以恢复安全检查点并在状态收敛后复用后缀。

这是实验候选。源码中的 `_密扫描策略.enabled`、`_增量策略.enabled` 均保持 `假`，由下面的实验构建器在 AST 中显式开启。本分支没有更新正式编译器 pin、正式构建器或产品验收条件。新增模块会被导入和解析，因此开关关闭也不代表兼容旧 pin；复现本候选应使用下面固定的如言版本。

## 改动与依赖

| 文件 | 作用 |
| --- | --- |
| `src/markdown_incremental.ru` | 有界检查点、深复制状态、修订坐标平移与后缀收敛 |
| `src/markdown_syntax.ru` | 按 HWND 与文档身份管理缓存，接入通知、扫描、发布和遗忘 |
| `src/markdown_policy.ru` | 保留原普通入口，增加批量 ASCII／围栏喂入路径 |
| `src/markdown_dense.ru` | 不可变 UTF-8 字符串借用适配与保守回退 |
| `src/markdown_ascii_kernel.ru` | 五个可由密编译器选中的受限扫描核 |
| `experiments/markdown-dense-manifest.json` | 密核输入、范围、类型及效果清单 |

固定构建工具为 [`ru-language@bf57f2e0e9bc1c3767a5824ad2976da2cceae889`](https://github.com/uppet/ru-language/tree/bf57f2e0e9bc1c3767a5824ad2976da2cceae889)。普通应用经 C 编译，选中的五个密核直接生成 LLVM 14；这是混合构建。需要 Windows x64、Python、Git、完整 LLVM 14、MSVC 链接环境及 `windres`。不可变字符串借用桥和实验清单构建能力依赖这个如言版本；尚未将增量方案拆成独立旧工具链版本。

原 `d964ea9` 预览包提供 `Scintilla.dll`、`Lexilla.dll`、`RuSyntax.dll` 及其 `BUILD.json`，实验工具验证后逐字节复用。`native/` 源码和 DLL ABI 均未修改。运行候选时不需要 Python 或 LLVM。

## 复现

在真实 Windows 上，将两个仓库放在同一父目录。以下命令从父目录运行；Git Bash 可用 `python3`，其他终端可改用对应的 Python 命令。`--runtime` 请替换成原 d964 预览包目录；所有输出目录必须尚不存在。

```sh
git clone https://github.com/uppet/ru_notepad.git ru_notepad-wij
git -C ru_notepad-wij switch wij
git clone https://github.com/uppet/ru-language.git ru-language-bs
git -C ru-language-bs switch --detach bf57f2e0e9bc1c3767a5824ad2976da2cceae889
python3 ru-language-bs/tools/prepare_workspace.py --with-llvm
```

构建对照组与增量组，两者都开启密核，只改变增量开关。这里直接使用已经包含改动的 `wij`，**不要再应用如言仓库里的 notepad 补丁**。

```sh
python3 ru-language-bs/experiments/notepad_undo/build.py --app-root ru_notepad-wij --runtime S:/Apps/ru_notepad --output ru_notepad-wij/build/wij-full --arm dense --target c-llvm
python3 ru-language-bs/experiments/notepad_undo/build.py --app-root ru_notepad-wij --runtime S:/Apps/ru_notepad --output ru_notepad-wij/build/wij-incremental --arm dense --target c-llvm --incremental
python3 ru-language-bs/experiments/notepad_undo/benchmark_incremental.py --app-root ru_notepad-wij --control ru_notepad-wij/build/wij-full --incremental ru_notepad-wij/build/wij-incremental --output ru_notepad-wij/build/wij-benchmark
```

构建器默认资源工具位于 `C:/msys64/mingw64/bin/windres.exe`，可通过 `--windres` 指定。LLVM 沿如言的工具链选择，亦可用 `RU_LLVM_CLANG` 指定 LLVM 14 的 Clang。详细参数见[固定构建工具说明](https://github.com/uppet/ru-language/blob/bf57f2e0e9bc1c3767a5824ad2976da2cceae889/experiments/notepad_undo/README.md)。

独立运行语义和真实控件对照；第一个也可在 Linux 上运行，第二个必须在真实 Windows 上运行：

```sh
python3 ru-language-bs/experiments/notepad_undo/check_incremental.py --app-root ru_notepad-wij --output ru_notepad-wij/build/wij-policy
python3 ru-language-bs/experiments/notepad_undo/check_incremental_native.py --app-root ru_notepad-wij --runtime S:/Apps/ru_notepad --output ru_notepad-wij/build/wij-native
```

## 已有验证与性能证据

以下是此前对这六份相同输入源码完成的本地实验，本次提交重新核对源码哈希，不把它们说成本分支新跑的 CI 或完整产品验收。固定的[完整报告及原始证据](https://github.com/uppet/ru-language/blob/bf57f2e0e9bc1c3767a5824ad2976da2cceae889/docs/notepad-incremental-2026-10-22.md)已随如言 `bs` 提交。

| 1 MB 未闭合围栏，中位数 | 密核＋全量扫描 | 密核＋增量扫描 |
| --- | ---: | ---: |
| 首次打开 | 15.704 s | 15.721 s |
| 插入字符 | 7.572 s | 0.525 s |
| 退格 | 7.583 s | 0.524 s |
| 连续两次 Undo | 15.140 s | 0.782 s |

每组各三个完整 GUI 进程，按全量／增量／增量／全量／全量／增量顺序执行，共 72 阶段通过。每次双撤销沿用同一个原 30 秒窗口，未放宽输入、绘制、文本、样式或折叠检查。耗时包含原观察器，属于本机端到端计时，不能当作纯 CPU 测量或 p95。普通多行与单长行 Undo 基本持平；多行打开、插入等阶段有变慢，全部数值保留在报告中。

- Linux 与真实 Windows 各比较 62 个修订、89,956 行折叠及最终全部 24 槽状态，包含 Unicode／CRLF、围栏结构改变、Setext 回溯标题、HTML、空文档和连续撤销文本；GC live 为零。
- 真实 Scintilla／Lexilla 另有 42 组逐行折叠、可见性与完整文本对照，包含真实 Undo、非零检查点恢复、多通知回退和缓存遗忘；GC live 为零。
- A/B 的应用源码、编译器、LLVM 密核及三份 DLL 相同，生成 C 只差一个事实值。参见[构建对照证明](https://github.com/uppet/ru-language/blob/bf57f2e0e9bc1c3767a5824ad2976da2cceae889/docs/notepad-incremental-2026-10-22/build-pair-proof.json)与[源码校验表](https://github.com/uppet/ru-language/blob/bf57f2e0e9bc1c3767a5824ad2976da2cceae889/docs/notepad-incremental-2026-10-22/source-checksums.json)。

## Review 重点与适用边界

缓存按编辑器 HWND 与文档身份隔离，最多 128 个冻结检查点，复制标题栈及 closer 标记，不保存全文或原生指针。首次可用边界约 1 KiB，后续通常至少间隔 16 KiB。恢复与比较按 UTF-8 字节坐标平移，其他状态逐项比较。

仅在上一修订完成、没有 pending、多通知或增减行、长度及行数复核通过时尝试复用。必须越过被编辑物理行、发布本次重算范围，并在无待定段落且标题全已确认的稳定状态上收敛。结构改变不收敛时继续到 EOF；不合格通知保守全量。缓存没有保存任意 Undo 历史快照。

标题稳定条件尤其需要保留：首轮原型仅比较状态就跳过后缀，遗漏 EOF 确认标题后的回溯补写，被原 GUI 门槛拒绝。最终代码已增加稳定条件，失败记录也保留在完整报告中。

原 35 字段 GUI 扫描状态、1024 字节读取、64 行发布、UI 时间预算，以及文档身份／线程／修订和借用生命周期约束均保留。增量缓存独立存储，取消、关闭及遗忘会清理对应身份。检查点上限下的长期编辑覆盖和淘汰策略仍可完善；局部重算区域仍可能发布相同折叠层级。

后续合入前需要由 `wip` 决定编译器升级、默认开关及正式构建入口，并补跑完整产品验收。本提交不宣称这些工作已经完成。
