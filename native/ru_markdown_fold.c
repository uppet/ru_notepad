/* Application-private bounded publication. Ru owns Markdown and scheduling. */
#include "ru_markdown_fold.h"
#include <string.h>

#if !defined(RU_MARKDOWN_FOLD_TEST) && !defined(_WIN64)
#error The production Markdown fold backend requires Windows x64.
#endif

typedef char FoldHeaderSize[(sizeof(RuMarkdownFoldPlan) == 32) ? 1 : -1];
typedef char FoldRangeSize[(sizeof(RuMarkdownFoldRange) == 16) ? 1 : -1];
typedef char FoldResultSize[(sizeof(RuMarkdownFoldResult) == 32) ? 1 : -1];

typedef struct FoldPlanStorage {
    RuMarkdownFoldPlan header;
    RuMarkdownFoldRange ranges[RU_MARKDOWN_FOLD_MAX_RANGES];
} FoldPlanStorage;
typedef char FoldStorageSize[(sizeof(FoldPlanStorage) == 1056) ? 1 : -1];

#ifndef RU_MARKDOWN_FOLD_TEST
typedef intptr_t (WINAPI *FoldDirect)(void *, UINT, uintptr_t, intptr_t);
#endif
typedef struct FoldContext {
    RuMarkdownFoldWindow hwnd, parent;
    RuMarkdownFoldModule module;
    void *opaque, *doc;
    intptr_t length;
    uint32_t lines;
#ifdef RU_MARKDOWN_FOLD_TEST
    uint32_t resolved;
#else
    FoldDirect direct;
#endif
} FoldContext;

/* The test-only platform substitutes do not exist in the shipped DLL. The
 * plan validator, qualification scheduling and commit loop below are shared. */
#ifdef RU_MARKDOWN_FOLD_TEST
#include "../tests/ru_markdown_fold_test_backend.h"
#else
static uint32_t fold_backend_get_error(void) { return (uint32_t)GetLastError(); }
static void fold_backend_set_error(uint32_t value) { SetLastError((DWORD)value); }

static int fold_backend_qualify(const FoldContext *context) {
    DWORD process = 0;
    DWORD thread;
    WCHAR class_name[16];
    if (!IsWindow(context->hwnd)) return 0;
    thread = GetWindowThreadProcessId(context->hwnd, &process);
    if (!thread || thread != GetCurrentThreadId() ||
        process != GetCurrentProcessId()) return 0;
    if (!IsWindow(context->parent)) return 0;
    thread = GetWindowThreadProcessId(context->parent, &process);
    if (!thread || thread != GetCurrentThreadId() ||
        process != GetCurrentProcessId()) return 0;
    if (GetClassNameW(context->hwnd, class_name, 16) != 9 ||
        memcmp(class_name, L"Scintilla", 10 * sizeof(WCHAR))) return 0;
    if (GetParent(context->hwnd) != context->parent) return 0;
    if ((HMODULE)(uintptr_t)GetClassLongPtrW(context->hwnd, GCLP_HMODULE) !=
        context->module) return 0;
    /* Pinned Scintilla 5.6.7 stores its object at pointer-sized extra slot 0.
     * Compare this before dereferencing a caller-supplied opaque pointer. */
    if ((void *)(uintptr_t)GetWindowLongPtrW(context->hwnd, 0) != context->opaque)
        return 0;
    return 1;
}

static int fold_backend_resolve(FoldContext *context) {
    FARPROC symbol = GetProcAddress(context->module, "Scintilla_DirectFunction");
    typedef char FoldFunctionPointerSize[
        (sizeof(FoldDirect) == sizeof(FARPROC)) ? 1 : -1];
    (void)sizeof(FoldFunctionPointerSize);
    if (!symbol) return 0;
    memcpy(&context->direct, &symbol, sizeof(context->direct));
    return 1;
}

static intptr_t fold_backend_direct(const FoldContext *context, unsigned int message,
                                    uintptr_t wparam, intptr_t lparam) {
    return context->direct(context->opaque, message, wparam, lparam);
}
#endif

/* All native getters are fixed private call sites. Qualification is repeated
 * before and after every direct dereference, even though the closed caller's
 * watcher/subclass contract prohibits callbacks on this path. */
static uint32_t fold_read(const FoldContext *context, unsigned int message,
                          intptr_t *value) {
    if (!fold_backend_qualify(context)) return RU_MARKDOWN_FOLD_STALE;
    *value = fold_backend_direct(context, message, 0, 0);
    if (!fold_backend_qualify(context)) return RU_MARKDOWN_FOLD_STALE;
    return RU_MARKDOWN_FOLD_OK;
}

static uint32_t fold_guard(const FoldContext *context, RuMarkdownFoldResult *result) {
    intptr_t doc, length, lines, mask, automatic, native_status;
    uint32_t status;
    status = fold_read(context, 2357, &doc); /* SCI_GETDOCPOINTER */
    if (status) return status;
    if ((void *)(uintptr_t)doc != context->doc) return RU_MARKDOWN_FOLD_STALE;
    status = fold_read(context, 2183, &length); /* SCI_GETLENGTH */
    if (status) return status;
    if (length != context->length) return RU_MARKDOWN_FOLD_STALE;
    status = fold_read(context, 2154, &lines); /* SCI_GETLINECOUNT */
    if (status) return status;
    if (lines < 1 || (uint64_t)lines != context->lines) return RU_MARKDOWN_FOLD_STALE;
    status = fold_read(context, 2378, &mask); /* SCI_GETMODEVENTMASK */
    if (status) return status;
    status = fold_read(context, 2664, &automatic); /* SCI_GETAUTOMATICFOLD */
    if (status) return status;
    status = fold_read(context, 2383, &native_status); /* SCI_GETSTATUS */
    if (status) return status;
    result->scintilla_status = (native_status < 0 || (uint64_t)native_status > UINT32_MAX)
        ? UINT32_MAX : (uint32_t)native_status;
    if (native_status != 0) return RU_MARKDOWN_FOLD_NATIVE_ERROR;
    if (mask != 3 || automatic != 0)
        return result->attempted ? RU_MARKDOWN_FOLD_STALE
                                : RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE;
    return RU_MARKDOWN_FOLD_OK;
}

/* These checks describe typed buffers, not an arbitrary pointer safety API. */
static int fold_envelope(const void *plan, uint32_t plan_bytes,
                          const void *result, uint32_t result_bytes) {
    uintptr_t p = (uintptr_t)plan, r = (uintptr_t)result;
    uintptr_t pe, re;
    if (!p || !r || (p % sizeof(uint32_t)) || (r % sizeof(uint32_t))) return 0;
    if (plan_bytes < RU_MARKDOWN_FOLD_HEADER_BYTES ||
        plan_bytes > RU_MARKDOWN_FOLD_MAX_PLAN_BYTES ||
        (plan_bytes - RU_MARKDOWN_FOLD_HEADER_BYTES) % RU_MARKDOWN_FOLD_RANGE_BYTES ||
        result_bytes != RU_MARKDOWN_FOLD_RESULT_BYTES) return 0;
    if (p > UINTPTR_MAX - plan_bytes || r > UINTPTR_MAX - result_bytes) return 0;
    pe = p + plan_bytes;
    re = r + result_bytes;
    return pe <= r || re <= p;
}

static int fold_plan_valid(const FoldPlanStorage *plan, uint32_t bytes) {
    const RuMarkdownFoldPlan *header = &plan->header;
    uint32_t index;
    if (header->version != RU_MARKDOWN_FOLD_ABI ||
        header->range_count > RU_MARKDOWN_FOLD_MAX_RANGES ||
        bytes != RU_MARKDOWN_FOLD_HEADER_BYTES +
                 header->range_count * RU_MARKDOWN_FOLD_RANGE_BYTES ||
        header->max_lines < 1 || header->max_lines > RU_MARKDOWN_FOLD_MAX_LINES ||
        header->expected_lines < 1 || header->reserved0 || header->reserved1 ||
        header->range_index > header->range_count) return 0;
    for (index = 0; index < header->range_count; ++index) {
        const RuMarkdownFoldRange *range = &plan->ranges[index];
        if (!range->count || range->depth > 6 || range->header > 1 ||
            (range->header && range->count != 1) ||
            range->start >= header->expected_lines ||
            range->count > header->expected_lines - range->start) return 0;
    }
    if (header->range_index == header->range_count) return header->range_offset == 0;
    return header->range_offset < plan->ranges[header->range_index].count;
}

static void fold_advance(const FoldPlanStorage *plan, RuMarkdownFoldResult *result) {
    ++result->next_offset;
    if (result->next_offset == plan->ranges[result->next_index].count) {
        ++result->next_index;
        result->next_offset = 0;
    }
}

static uint32_t fold_apply(FoldContext *context, const void *input,
                           uint32_t input_bytes, void *output, uint32_t output_bytes) {
    FoldPlanStorage plan;
    RuMarkdownFoldResult result;
    uint32_t status;
    if (!fold_envelope(input, input_bytes, output, output_bytes))
        return RU_MARKDOWN_FOLD_BAD_ARGUMENT;
    memset(&result, 0, sizeof(result));
    if (!context->hwnd || !context->parent || !context->module || !context->opaque ||
        !context->doc || context->length < 0 ||
        (uint64_t)context->length > RU_MARKDOWN_FOLD_MAX_DOCUMENT_BYTES) {
        status = RU_MARKDOWN_FOLD_BAD_ARGUMENT;
        goto finished;
    }
    memcpy(&plan, input, input_bytes);
    if (!fold_plan_valid(&plan, input_bytes) ||
        (uint64_t)plan.header.expected_lines > (uint64_t)context->length + 1u) {
        status = RU_MARKDOWN_FOLD_BAD_PLAN;
        goto finished;
    }
    result.next_index = plan.header.range_index;
    result.next_offset = plan.header.range_offset;
    context->lines = plan.header.expected_lines;
    if (!fold_backend_qualify(context)) {
        status = RU_MARKDOWN_FOLD_STALE;
        goto finished;
    }
    if (!fold_backend_resolve(context)) {
        status = RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE;
        goto finished;
    }
    status = fold_guard(context, &result);
    if (status) goto finished;
    while (result.next_index < plan.header.range_count &&
           result.attempted < plan.header.max_lines) {
        const RuMarkdownFoldRange *range = &plan.ranges[result.next_index];
        uint32_t line = range->start + result.next_offset;
        intptr_t level = (intptr_t)(0x400u + range->depth +
                                   (range->header ? 0x2000u : 0u));
        status = fold_guard(context, &result);
        if (status) goto finished;
        if (!fold_backend_qualify(context)) {
            status = RU_MARKDOWN_FOLD_STALE;
            goto finished;
        }
        ++result.attempted;
        fold_advance(&plan, &result);
        (void)fold_backend_direct(context, 2222, line, level); /* SCI_SETFOLDLEVEL */
        status = fold_guard(context, &result);
        if (status) goto finished;
        ++result.completed;
    }
    status = RU_MARKDOWN_FOLD_OK;
finished:
    result.status = status;
    memcpy(output, &result, sizeof(result));
    return status;
}

RU_MARKDOWN_FOLD_API uint32_t ru_markdown_fold_abi(void) {
    return RU_MARKDOWN_FOLD_ABI;
}

RU_MARKDOWN_FOLD_API uint32_t ru_markdown_fold_apply_v1(
    RuMarkdownFoldWindow hwnd, RuMarkdownFoldWindow expected_parent,
    RuMarkdownFoldModule expected_module, void *opaque_direct, void *expected_doc,
    intptr_t expected_length, const void *plan, uint32_t plan_bytes,
    void *result, uint32_t result_bytes) {
    uint32_t last_error = fold_backend_get_error();
    uint32_t status;
    FoldContext context;
    memset(&context, 0, sizeof(context));
    context.hwnd = hwnd;
    context.parent = expected_parent;
    context.module = expected_module;
    context.opaque = opaque_direct;
    context.doc = expected_doc;
    context.length = expected_length;
    status = fold_apply(&context, plan, plan_bytes, result, result_bytes);
    fold_backend_set_error(last_error);
    return status;
}
