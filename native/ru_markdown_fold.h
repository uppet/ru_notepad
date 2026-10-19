#ifndef RU_NOTEPAD_MARKDOWN_FOLD_H
#define RU_NOTEPAD_MARKDOWN_FOLD_H

#include <stdint.h>
#include <stddef.h>
#ifdef _WIN32
#include <windows.h>
#define RU_MARKDOWN_FOLD_API __declspec(dllexport)
typedef HWND RuMarkdownFoldWindow;
typedef HMODULE RuMarkdownFoldModule;
#else
#define RU_MARKDOWN_FOLD_API __attribute__((visibility("default")))
typedef void *RuMarkdownFoldWindow;
typedef void *RuMarkdownFoldModule;
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define RU_MARKDOWN_FOLD_ABI 0x00010000u
#define RU_MARKDOWN_FOLD_MAX_RANGES 64u
#define RU_MARKDOWN_FOLD_MAX_LINES 64u
#define RU_MARKDOWN_FOLD_HEADER_BYTES 32u
#define RU_MARKDOWN_FOLD_RANGE_BYTES 16u
#define RU_MARKDOWN_FOLD_RESULT_BYTES 32u
#define RU_MARKDOWN_FOLD_MAX_PLAN_BYTES 1056u
#define RU_MARKDOWN_FOLD_MAX_DOCUMENT_BYTES 32000000u

enum {
    RU_MARKDOWN_FOLD_OK = 0,
    RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE = 1,
    RU_MARKDOWN_FOLD_STALE = 2,
    RU_MARKDOWN_FOLD_BAD_PLAN = 3,
    RU_MARKDOWN_FOLD_NATIVE_ERROR = 4,
    RU_MARKDOWN_FOLD_BAD_ARGUMENT = 5
};

/* Windows x64 little-endian wire ABI; all fields are exactly uint32_t.
 * plan_bytes MUST equal 32 + range_count * 16, result_bytes MUST equal 32.
 * The header is followed immediately by range_count ranges. Buffers are
 * caller-owned, naturally u32-aligned, nonoverlapping, valid for the complete
 * call, and borrowed only. The helper copies the bounded plan onto its stack.
 * Address-envelope checks cannot validate arbitrary hostile/unmapped pointers.
 */
typedef struct RuMarkdownFoldPlan {
    uint32_t version, range_count, range_index, range_offset;
    uint32_t expected_lines, max_lines, reserved0, reserved1;
} RuMarkdownFoldPlan;

typedef struct RuMarkdownFoldRange {
    uint32_t start, count, depth, header;
} RuMarkdownFoldRange;

typedef struct RuMarkdownFoldResult {
    uint32_t status, attempted, completed, next_index;
    uint32_t next_offset, scintilla_status, reserved0, reserved1;
} RuMarkdownFoldResult;

/* Plan rules: version==ABI, range_count<=64, max_lines in [1,64],
 * expected_length in [0,32000000], expected_lines in [1,expected_length+1],
 * reserved fields zero. Every range has count>=1,
 * depth<=6, header in [0,1], header implies count==1, and start+count
 * fits expected_lines without overflow. The entire plan is checked before
 * any fold write, including ranges beyond the cursor/current batch.
 * Cursor: index<count => offset<ranges[index].count; index==count => offset=0.
 * An empty plan with cursor (0,0), or an end cursor, is a valid guarded no-op.
 * At most max_lines fixed SCI_SETFOLDLEVEL(2222) calls occur per invocation;
 * each writes 0x400 + depth, plus 0x2000 when header is 1.
 *
 * attempted increments immediately BEFORE each 2222 call; the output cursor
 * advances past that attempted call even when the postguard fails.
 * completed increments only AFTER the complete postguard and GETSTATUS==0.
 * Thus 0<=completed<=attempted<=64, and an uncertain final write is counted
 * as attempted but not completed. OK has attempted==completed. Only OK with
 * independently verified counts/cursor may advance the Ru scheduler.
 * Any non-OK after an attempt invalidates the epoch: never replay or resume
 * its diagnostic cursor, including a possibly committed final assignment.
 *
 * Status: BAD_ARGUMENT for invalid/null arguments, lengths, alignment,
 * address overflow or overlapping plan/result. An invalid buffer envelope
 * leaves result untouched. Other valid-envelope returns initialize all result
 * fields and mirror the returned status; pre-plan failures have cursor (0,0).
 * BAD_PLAN covers all wire/plan/cursor errors, with no native dereference.
 * STALE covers window/process/thread/class/parent/module/context identity,
 * document/length/line-count mismatches, and configuration changes after
 * an attempt. NATIVE_ERROR reports a nonzero Scintilla status.
 * INELIGIBLE_PREWRITE covers unavailable named direct export, notification
 * mask!=3, or automatic folding!=0, only with attempted==completed==0.
 * Only this INELIGIBLE result permits a freshly revalidated ordinary fallback.
 *
 * The caller must hold the closed application capability: pinned Scintilla
 * module, exclusive owned document, known subclass/watcher configuration,
 * valid owner epoch, and no concurrent access/mutation of buffers or document.
 * These facts cannot be inferred merely from an HWND. Native qualification
 * checks live child/parent owner process/current thread, exact child class,
 * parent identity, class module,
 * and pointer-sized HWND extra-byte slot 0==opaque_direct before every direct
 * getter/write. There is no callback argument, arbitrary message dispatch,
 * SendMessage, allocation, retained pointer, or Markdown algorithm here.
 * The caller must independently recheck its capability/epoch after return.
 * LastError is preserved on every actual Windows path.
 */
RU_MARKDOWN_FOLD_API uint32_t ru_markdown_fold_abi(void);
RU_MARKDOWN_FOLD_API uint32_t ru_markdown_fold_apply_v1(
    RuMarkdownFoldWindow hwnd,
    RuMarkdownFoldWindow expected_parent,
    RuMarkdownFoldModule expected_module,
    void *opaque_direct,
    void *expected_doc,
    intptr_t expected_length,
    const void *plan,
    uint32_t plan_bytes,
    void *result,
    uint32_t result_bytes);

#ifdef __cplusplus
}
#endif
#endif
