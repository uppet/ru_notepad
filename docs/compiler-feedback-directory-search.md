# Ru feedback from the directory-search increment

Compiler snapshot: `c3bb177c6a15e90821e5495cc74b0fdfc39b893a`. No compiler source or production analysis limit was changed for this work.

## Supported type inspection would improve defensive APIs

The streaming text policy uses numeric byte/scalar arrays produced by a validated native adapter. It checks numeric ranges, missing fields, state transitions and bounds. It cannot promise a structured error for every arbitrary wrong-type caller value without a nonthrowing type predicate.

A minimal example is a string-to-number ordering comparison inside `试` / `救`. Both the interpreter and emitted C terminate with a runtime type error before reaching the rescue or following statement. Interpreter diagnostic: `大小比较需要两个数或两个句`; C diagnostic: `比较需要相同的数字或字符串类型`.

This agrees with the documented treatment of ordinary runtime errors. It is an API improvement request, not an asserted compiler defect: a supported value-kind predicate or guarded-validation API would let reusable libraries reject malformed caller values without first performing an invalid operation. The current editor adapter constructs typed numeric arrays, so directory file bytes are not exposed to this arbitrary-container boundary.

## Large inline numeric fixtures can dominate C compilation

A generated differential fixture containing repeated long numeric byte-array literals exceeded the stock C compilation timeout. Replacing only repeated fixture literals with bounded array construction allowed the unmodified compiler and GCC to build within the existing timeout. The actual production module and expected bytes remained unchanged. The final 4,650-result interpreter/C differential run had identical full output.

This is test-input construction cost, not evidence of a production decoder or compiler correctness defect. A future compact constant-data representation could make large native test corpora cheaper to compile; preserve default acceptance limits when investigating it.

## Full-application analysis remains a separate limitation

The full editor continues to exceed the default 200,000-step native-signature analysis budget. The directory increment adds three modules, but this limitation already existed before directory search. Any isolated higher-budget ABI oracle is development evidence only, not a successful default C build and not stage3/LLVM/Windows acceptance. Exact final-source measurements belong to the generated native-oracle evidence, not a historical number copied into this note.

## Useful existing capability

The owned-memory `读U32LE阵` operation makes fixed-layout native event decoding practical without borrowed pointers or scalar wrapper churn. Opaque 64-bit file identities and timestamps remain exact as two 32-bit words rather than conversion through the language's binary64 numbers. Explicit typed bindings and pointer-to-integer reinterpretation also make the native argument audit useful at this boundary.
