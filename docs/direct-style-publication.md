# Guarded style publication in 0.1.6

The 0.1.6 [product acceptance](https://github.com/uppet/ru_notepad/actions/runs/38984124830)
and [same-run comparison](https://github.com/uppet/ru_notepad/actions/runs/38984124849)
passed, and both original packages passed independent verification. Two GUI
pairs observed 10.248–11.456 seconds with direct publication versus
15.126–15.128 seconds through messages. This is a bounded same-run observation,
not a general performance guarantee. Later candidates retain this ownership
contract and need their own complete acceptance.

## Scope

Ru still decides every keyword, byte style, structural pairing and fold level.
The existing bounded scanner, event decoder, checkpoints, scheduling budget and
32,000,000-byte plain-text fallback remain in place. The 0.1.6 production
optimization is how an eligible editor receives three style operations:

- `SCI_STARTSTYLING` (2032)
- `SCI_SETSTYLING` (2033)
- `SCI_SETSTYLINGEX` (2073)

Scintilla's documented Windows `Scintilla_DirectFunction` export accepts the
same operations as its message interface. Ru binds that named export through
the existing fixed Windows x64 native-call ABI. There is no arbitrary function
pointer call, new language primitive, extra runtime DLL or native replacement
for Ru's lexical policy. See the upstream [direct-access contract](https://www.scintilla.org/ScintillaDoc.html#DirectAccess).

## Ownership and fallback

Only main-application editors explicitly registered as owning an exclusive
document may use the optimization. Eligibility checks cover the actual owning
thread and parent window, current styling state and generation, document,
revision, length, and the text-only modification notification mask (`3`).
Unregistered editors and the existing default-full-notification core fixture
retain message-based publication.

The complete batch is validated before its first mutation. The real
`SCI_GETDIRECTPOINTER` result is borrowed only for the subsequent non-pumping
style segment; it is neither converted to an ordinary Ru number nor cached
across batches or document lifetimes. The style buffer stays owned until its
synchronous call returns. An unregistered editor or an ineligible notification
mask/configuration chooses the original route before publication. A batch whose
document, generation or revision has become stale is rejected rather than
published through a fallback. A partially applied failing batch is never
replayed through a different route.

Fold-level publication (`2222`) remains message-based because automatic fold
changes can update scrollbars and introduce additional synchronous window
activity. The borrowed pointer is no longer used when fold/status operations
begin. Existing Scintilla status clearing/checking and native callback-error
handling remain required. Editing, undo, document loading/saving, drag/drop and
window destruction continue through their existing paths.

## Required evidence

The new 36-assertion real Windows suite must compare complete text, byte styles, fold levels, dirty
state and undo behavior for eligible direct publication and the original route.
They must also exercise registration rejection, multiple windows, language
switching, document replacement and close/recreation. A native route probe must
prove that the three style messages bypass the child subclass when eligible and
reach it through the original route in the positive control. A fast run in which
every batch silently fell back would not establish direct-call performance.

The paired benchmark uses the same candidate and common initialization. Its
copied test graphs differ only in the private route-enable value. Eight
interleaved runs cover both routes twice in cooperative-console and detached-GUI
paths. The exact 1,000,000-byte Chinese corpus, full-output checks, 30-second
completion deadline, six edit probes, real navigation/paint handling and normal
close remain mandatory. Timings and process elapsed values have distinct
boundaries. Two repeats do not support broad statistical or Notepad++ parity
claims.

The earlier [twenty-row profiling study](https://github.com/uppet/ru_notepad/actions/runs/38974348790)
is a fixed historical baseline, not a license to accept changed production
inputs under its old source hashes. It observed 233,626 child-subclass callbacks
inside style publication in each instrumented main-application path. Its fixed
periodic samples identify a useful experiment, but cannot be multiplied into an
unbiased total-time estimate. The application must separately pass its complete
native safety and packaging gates before any new package is accepted.
