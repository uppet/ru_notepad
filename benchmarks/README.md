# Performance acceptance plan

No Windows application benchmark has run yet. Native cross-build duration is not UI performance.

For each accepted Windows build, record OS version, CPU/RAM/storage, executable hash, Scintilla version, file encoding and byte size, cold/warm state, five repetitions, median and worst observation. Record failures and cancellations separately.

Initial corpus: 1 KiB, 100 KiB, 1 MiB and 4 MiB UTF-8; CRLF/LF/mixed endings; one long line; 100,000 short lines; CJK and emoji. The preview explicitly rejects files or UTF-8 editor loads over 4 MiB. Do not advertise large-file performance from these small-file tests.

Measure startup to editable caret, open to editable caret, tab switch, first/next search, worst-case absent search, replace-all plus undo, encode/save/flush and close-all confirmation. Observe peak working set, handles and responsiveness over repeated open/close cycles. Use copies on a local test filesystem. Separate filesystem flush time from editor operations.

Later gates expand to 10/100/500 MiB only after the current cap is deliberately redesigned and tested. Cancellation, memory pressure, single-long-line layout, background search and encoding expansion are separate acceptance cases.
