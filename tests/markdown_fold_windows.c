/* Actual Windows-only ABI control. This is a test executable, never shipped.
 * It loads the two current, absolute-path runtime DLLs supplied by the runner. */
#include "../native/ru_markdown_fold.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

typedef uint32_t (*AbiFunction)(void);
typedef uint32_t (*ApplyFunction)(HWND, HWND, HMODULE, void *, void *, intptr_t,
                                const void *, uint32_t, void *, uint32_t);
typedef struct TestPlan {
    RuMarkdownFoldPlan header;
    RuMarkdownFoldRange ranges[64];
} TestPlan;
typedef struct TestWindow {
    HWND parent, hwnd;
    void *opaque, *doc;
    intptr_t length;
} TestWindow;
typedef struct ThreadWindow {
    HANDLE ready, stop;
    HMODULE scintilla;
    TestWindow window;
    uint32_t created, unchanged, timed_out;
} ThreadWindow;

static unsigned checks;
static ApplyFunction apply;
static HMODULE scintilla;
static TestPlan plan;
static RuMarkdownFoldResult result;

static void check(int value, const char *case_id) {
    ++checks;
    if (!value) {
        /* Fixed identifiers only: no memory, document text or paths. */
        fprintf(stderr, "FAIL %s\n", case_id);
        exit(1);
    }
}

static int create_window(TestWindow *window, HMODULE instance) {
    char text[200];
    unsigned i;
    memset(window, 0, sizeof(*window));
    window->parent = CreateWindowExW(0, L"STATIC", L"fold-control", WS_OVERLAPPED,
                                     0, 0, 200, 100, NULL, NULL, NULL, NULL);
    if (!window->parent) return 0;
    window->hwnd = CreateWindowExW(0, L"Scintilla", L"", WS_CHILD,
                                  0, 0, 200, 100, window->parent, NULL, instance, NULL);
    if (!window->hwnd) { DestroyWindow(window->parent); return 0; }
    for (i = 0; i < 99; ++i) { text[2*i] = 'x'; text[2*i+1] = '\n'; }
    text[198] = 'x'; text[199] = 0;
    SendMessageW(window->hwnd, 2359, 3, 0); /* SETMODEVENTMASK */
    SendMessageW(window->hwnd, 2663, 0, 0); /* SETAUTOMATICFOLD */
    SendMessageW(window->hwnd, 2181, 0, (LPARAM)text); /* SETTEXT */
    window->opaque = (void *)SendMessageW(window->hwnd, 2185, 0, 0);
    window->doc = (void *)SendMessageW(window->hwnd, 2357, 0, 0);
    window->length = (intptr_t)SendMessageW(window->hwnd, 2183, 0, 0);
    return window->opaque && window->doc && window->length == 199 &&
        SendMessageW(window->hwnd, 2154, 0, 0) == 100;
}

static void reset_plan(TestWindow *window) {
    unsigned i;
    memset(&plan, 0, sizeof(plan));
    plan.header.version = RU_MARKDOWN_FOLD_ABI;
    plan.header.range_count = 1;
    plan.header.expected_lines = 100;
    plan.header.max_lines = 64;
    plan.ranges[0].count = 100;
    plan.ranges[0].depth = 2;
    memset(&result, 0xa5, sizeof(result));
    for (i = 0; i < 100; ++i) SendMessageW(window->hwnd, 2222, i, 1024);
}

static void unchanged(const TestWindow *window) {
    unsigned i;
    for (i = 0; i < 100; ++i)
        check(SendMessageW(window->hwnd, 2223, i, 0) == 1024, "zero_write_levels");
}

static uint32_t invoke(const TestWindow *window, HWND expected_parent,
                       HMODULE expected_module, void *opaque, void *doc,
                       intptr_t length, uint32_t plan_bytes, uint32_t result_bytes) {
    uint32_t status;
    SetLastError(0x1234abcd);
    status = apply(window->hwnd, expected_parent, expected_module, opaque, doc,
                   length, &plan, plan_bytes, &result, result_bytes);
    check(GetLastError() == 0x1234abcd, "last_error_preserved");
    if (result_bytes == 32 && plan_bytes == 48) {
        check(result.status == status, "status_mirrored");
        check(!result.reserved0 && !result.reserved1, "reserved_zero");
        check(result.completed <= result.attempted && result.attempted <= 64,
              "bounded_accounting");
    }
    return status;
}

static uint32_t standard(const TestWindow *window) {
    return invoke(window, window->parent, scintilla, window->opaque, window->doc,
                  window->length, 48, 32);
}

static DWORD WINAPI foreign_thread(void *argument) {
    ThreadWindow *thread = (ThreadWindow *)argument;
    DWORD wait;
    unsigned line;
    MSG message;
    thread->created = (uint32_t)create_window(&thread->window, thread->scintilla);
    SetEvent(thread->ready);
    if (!thread->created) return 1;
    for (;;) {
        wait = MsgWaitForMultipleObjects(1, &thread->stop, FALSE, 10000, QS_ALLINPUT);
        if (wait == WAIT_OBJECT_0) break;
        if (wait != WAIT_OBJECT_0 + 1) { thread->timed_out = 1; break; }
        while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    thread->unchanged = 1;
    for (line = 0; line < 100; ++line) {
        if (SendMessageW(thread->window.hwnd, 2223, line, 0) != 1024)
            thread->unchanged = 0;
    }
    DestroyWindow(thread->window.hwnd);
    DestroyWindow(thread->window.parent);
    return thread->timed_out ? 2 : 0;
}

int wmain(int argc, wchar_t **argv) {
    wchar_t root[32768], path[32768];
    HMODULE helper;
    FARPROC symbol;
    AbiFunction abi;
    TestWindow window, dead;
    TestPlan saved_plan;
    RuMarkdownFoldResult saved_result;
    ThreadWindow thread;
    HANDLE worker;
    DWORD thread_id, exit_code, full_path_length;
    unsigned i;
    size_t length;
    check(argc == 2, "runtime_argument");
    full_path_length = GetFullPathNameW(argv[1], 32768, root, NULL);
    check(full_path_length > 0 && full_path_length < 32768, "absolute_runtime");
    length = wcslen(root);
    check(length < 32740, "runtime_path_bound");
    memcpy(path, root, (length+1) * sizeof(wchar_t));
    wcscat(path, L"\\Scintilla.dll");
    scintilla = LoadLibraryExW(path, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    check(scintilla != NULL, "load_scintilla");
    memcpy(path, root, (length+1) * sizeof(wchar_t));
    wcscat(path, L"\\RuSyntax.dll");
    helper = LoadLibraryExW(path, NULL,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    check(helper != NULL, "load_helper");
    symbol = GetProcAddress(helper, "ru_markdown_fold_abi");
    check(symbol != NULL && sizeof(symbol) == sizeof(abi), "abi_export");
    memcpy(&abi, &symbol, sizeof(abi));
    symbol = GetProcAddress(helper, "ru_markdown_fold_apply_v1");
    check(symbol != NULL && sizeof(symbol) == sizeof(apply), "apply_export");
    memcpy(&apply, &symbol, sizeof(apply));
    SetLastError(0x1234abcd);
    check(abi() == RU_MARKDOWN_FOLD_ABI, "abi_version");
    check(GetLastError() == 0x1234abcd, "abi_last_error");
    check(create_window(&window, scintilla), "create_owned_scintilla");
    reset_plan(&window);
    check(standard(&window) == RU_MARKDOWN_FOLD_OK, "full_batch");
    check(result.attempted == 64 && result.completed == 64 &&
          result.next_index == 0 && result.next_offset == 64, "full_batch_counts");
    for (i = 0; i < 100; ++i)
        check(SendMessageW(window.hwnd, 2223, i, 0) == (i < 64 ? 1026 : 1024),
              "full_batch_levels");
    plan.header.range_offset = 64;
    check(standard(&window) == 0 && result.attempted == 36 && result.completed == 36 &&
          result.next_index == 1 && result.next_offset == 0, "resume_batch");
    for (i = 0; i < 100; ++i)
        check(SendMessageW(window.hwnd, 2223, i, 0) == 1026, "resume_levels");
    plan.header.range_offset = 0; plan.ranges[0].count = 1;
    plan.ranges[0].depth = 1; plan.ranges[0].header = 1;
    check(standard(&window) == 0 && result.completed == 1, "header_assignment");
    check(SendMessageW(window.hwnd, 2223, 0, 0) == 9217, "header_level");

    reset_plan(&window);
    check(invoke(&window, window.parent, scintilla,
          (void *)((uintptr_t)window.opaque ^ 8u), window.doc, window.length, 48, 32)
          == RU_MARKDOWN_FOLD_STALE, "forged_context");
    check(!result.attempted, "forged_context_no_attempt"); unchanged(&window);
    check(invoke(&window, window.hwnd, scintilla, window.opaque, window.doc,
          window.length, 48, 32) == RU_MARKDOWN_FOLD_STALE, "wrong_parent");
    check(invoke(&window, window.parent, GetModuleHandleW(L"kernel32.dll"), window.opaque,
          window.doc, window.length, 48, 32) == RU_MARKDOWN_FOLD_STALE, "wrong_module");
    check(invoke(&window, window.parent, scintilla, window.opaque,
          (void *)((uintptr_t)window.doc ^ 8u), window.length, 48, 32)
          == RU_MARKDOWN_FOLD_STALE, "wrong_document");
    check(invoke(&window, window.parent, scintilla, window.opaque, window.doc,
          window.length+1, 48, 32) == RU_MARKDOWN_FOLD_STALE, "wrong_length");
    check(invoke(&window, window.parent, scintilla, window.opaque, window.doc,
          32000001, 48, 32) == RU_MARKDOWN_FOLD_BAD_ARGUMENT, "oversize_document");
    plan.header.expected_lines = 101;
    check(standard(&window) == RU_MARKDOWN_FOLD_STALE, "wrong_lines");
    plan.header.expected_lines = 201;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "impossible_lines");
    plan.header.expected_lines = 100;
    SendMessageW(window.hwnd, 2359, 0, 0);
    check(standard(&window) == RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE, "mask_gate");
    check(!result.attempted && !result.completed, "mask_gate_no_attempt");
    SendMessageW(window.hwnd, 2359, 3, 0);
    SendMessageW(window.hwnd, 2663, 1, 0);
    check(standard(&window) == RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE, "autofold_gate");
    check(!result.attempted && !result.completed, "autofold_gate_no_attempt");
    SendMessageW(window.hwnd, 2663, 0, 0);
    SendMessageW(window.hwnd, 2382, 1, 0);
    check(standard(&window) == RU_MARKDOWN_FOLD_NATIVE_ERROR, "native_status_gate");
    check(result.scintilla_status == 1 && !result.attempted, "native_status_result");
    SendMessageW(window.hwnd, 2382, 0, 0);
    unchanged(&window);

    reset_plan(&window); plan.header.version++;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "wrong_plan_abi");
    reset_plan(&window); plan.header.max_lines = 65;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "oversize_batch");
    reset_plan(&window); plan.header.max_lines = 0;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "zero_batch");
    reset_plan(&window); plan.ranges[0].start = UINT32_MAX;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "range_overflow");
    reset_plan(&window); plan.header.range_offset = 100;
    check(standard(&window) == RU_MARKDOWN_FOLD_BAD_PLAN, "invalid_cursor");
    reset_plan(&window); plan.header.range_count = 64; plan.header.max_lines = 1;
    for (i = 0; i < 64; ++i) plan.ranges[i].count = 1;
    plan.ranges[63].depth = 7;
    check(invoke(&window, window.parent, scintilla, window.opaque, window.doc,
          window.length, 1056, 32) == RU_MARKDOWN_FOLD_BAD_PLAN, "invalid_final_range");
    check(!result.attempted, "invalid_final_range_no_attempt"); unchanged(&window);
    reset_plan(&window); saved_result = result;
    check(invoke(&window, window.parent, scintilla, window.opaque, window.doc,
          window.length, 48, 31) == RU_MARKDOWN_FOLD_BAD_ARGUMENT, "short_result");
    check(!memcmp(&result, &saved_result, sizeof(result)), "short_result_untouched");
    check(invoke(&window, window.parent, scintilla, window.opaque, window.doc,
          window.length, 47, 32) == RU_MARKDOWN_FOLD_BAD_ARGUMENT, "short_plan");
    check(!memcmp(&result, &saved_result, sizeof(result)), "short_plan_untouched");
    saved_plan = plan; SetLastError(0x1234abcd);
    check(apply(window.hwnd, window.parent, scintilla, window.opaque, window.doc,
          window.length, &plan, 48, &plan, 32) == RU_MARKDOWN_FOLD_BAD_ARGUMENT,
          "buffer_overlap");
    check(GetLastError() == 0x1234abcd, "overlap_last_error");
    check(!memcmp(&plan, &saved_plan, sizeof(plan)), "overlap_untouched");
    unchanged(&window);

    memset(&thread, 0, sizeof(thread)); thread.scintilla = scintilla;
    thread.ready = CreateEventW(NULL, TRUE, FALSE, NULL);
    thread.stop = CreateEventW(NULL, TRUE, FALSE, NULL);
    check(thread.ready && thread.stop, "foreign_thread_events");
    worker = CreateThread(NULL, 0, foreign_thread, &thread, 0, &thread_id);
    check(worker != NULL, "foreign_thread_create");
    check(WaitForSingleObject(thread.ready, 10000) == WAIT_OBJECT_0 && thread.created,
          "foreign_window_ready");
    check(GetWindowThreadProcessId(thread.window.hwnd, NULL) != GetCurrentThreadId(),
          "foreign_window_thread_verified");
    reset_plan(&window);
    check(standard(&thread.window) == RU_MARKDOWN_FOLD_STALE, "cross_thread_gate");
    check(!result.attempted && !result.completed, "cross_thread_no_attempt");
    check(SetEvent(thread.stop), "foreign_thread_stop");
    check(WaitForSingleObject(worker, 10000) == WAIT_OBJECT_0, "foreign_thread_join");
    check(GetExitCodeThread(worker, &exit_code) && exit_code == 0 &&
          thread.unchanged && !thread.timed_out, "foreign_thread_unchanged");
    CloseHandle(worker); CloseHandle(thread.ready); CloseHandle(thread.stop);

    dead = window;
    check(DestroyWindow(window.hwnd), "owned_window_destroy");
    check(standard(&dead) == RU_MARKDOWN_FOLD_STALE, "destroyed_window_gate");
    check(!result.attempted && !result.completed, "destroyed_window_no_attempt");
    check(DestroyWindow(window.parent), "owned_parent_destroy");
    FreeLibrary(helper); FreeLibrary(scintilla);
    printf("{\"kind\":\"windows_runtime\",\"checks\":%u,\"cross_thread\":true,"
           "\"real_windows_runtime\":true,\"ok\":true}\n", checks);
    return 0;
}
