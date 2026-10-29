#ifndef RU_MARKDOWN_FOLD_TEST
#error This backend is never part of the production build.
#endif

/* Compile-time fake platform for the SAME validator and bounded commit loop.
 * All fault controls and arbitrary test state are absent from the DLL. */
typedef struct FoldFake {
    void *hwnd, *parent, *module, *opaque, *doc;
    intptr_t length, lines, mask, automatic, status;
    uint32_t alive, class_ok, export_available;
    uint32_t current_process, owner_process, current_thread, owner_thread;
    uint32_t parent_alive, parent_process, parent_thread;
    uint32_t last_error, qualifications, direct_calls, writes, bad_dereference;
    uint32_t fail_qualification, mutate_after_write, mutation;
    uintptr_t written_lines[64];
    intptr_t written_levels[64];
} FoldFake;
static FoldFake fold_fake;

enum { FAKE_DESTROY = 1, FAKE_DOC, FAKE_LENGTH, FAKE_LINES, FAKE_MASK,
       FAKE_AUTOMATIC, FAKE_STATUS, FAKE_OPAQUE, FAKE_THREAD, FAKE_PARENT,
       FAKE_MODULE, FAKE_PROCESS, FAKE_CLASS, FAKE_PARENT_THREAD,
       FAKE_PARENT_PROCESS, FAKE_PARENT_DEAD };

static int fold_fake_matches(const FoldContext *context) {
    return fold_fake.alive && fold_fake.parent_alive && fold_fake.class_ok &&
        fold_fake.hwnd == context->hwnd && fold_fake.parent == context->parent &&
        fold_fake.module == context->module && fold_fake.opaque == context->opaque &&
        fold_fake.current_process == fold_fake.owner_process &&
        fold_fake.current_thread == fold_fake.owner_thread &&
        fold_fake.current_process == fold_fake.parent_process &&
        fold_fake.current_thread == fold_fake.parent_thread;
}
static uint32_t fold_backend_get_error(void) { return fold_fake.last_error; }
static void fold_backend_set_error(uint32_t value) { fold_fake.last_error = value; }
static int fold_backend_qualify(const FoldContext *context) {
    ++fold_fake.qualifications;
    fold_fake.last_error = 123;
    if (fold_fake.fail_qualification == fold_fake.qualifications) return 0;
    return fold_fake_matches(context);
}
static int fold_backend_resolve(FoldContext *context) {
    fold_fake.last_error = 234;
    context->resolved = fold_fake.export_available;
    return context->resolved != 0;
}
static void fold_fake_mutate(void) {
    switch (fold_fake.mutation) {
    case FAKE_DESTROY: fold_fake.alive = 0; break;
    case FAKE_DOC: fold_fake.doc = (void *)(uintptr_t)0x7777; break;
    case FAKE_LENGTH: ++fold_fake.length; break;
    case FAKE_LINES: ++fold_fake.lines; break;
    case FAKE_MASK: fold_fake.mask = 0; break;
    case FAKE_AUTOMATIC: fold_fake.automatic = 1; break;
    case FAKE_STATUS: fold_fake.status = 1000; break;
    case FAKE_OPAQUE: fold_fake.opaque = (void *)(uintptr_t)0x7777; break;
    case FAKE_THREAD: ++fold_fake.owner_thread; break;
    case FAKE_PARENT: fold_fake.parent = (void *)(uintptr_t)0x7777; break;
    case FAKE_MODULE: fold_fake.module = (void *)(uintptr_t)0x7777; break;
    case FAKE_PROCESS: ++fold_fake.owner_process; break;
    case FAKE_CLASS: fold_fake.class_ok = 0; break;
    case FAKE_PARENT_THREAD: ++fold_fake.parent_thread; break;
    case FAKE_PARENT_PROCESS: ++fold_fake.parent_process; break;
    case FAKE_PARENT_DEAD: fold_fake.parent_alive = 0; break;
    }
}
static intptr_t fold_backend_direct(const FoldContext *context, unsigned int message,
                                    uintptr_t wparam, intptr_t lparam) {
    ++fold_fake.direct_calls;
    fold_fake.last_error = 345;
    if (!context->resolved || !fold_fake_matches(context)) {
        ++fold_fake.bad_dereference;
        return 0;
    }
    switch (message) {
    case 2357: return (intptr_t)fold_fake.doc;
    case 2183: return fold_fake.length;
    case 2154: return fold_fake.lines;
    case 2378: return fold_fake.mask;
    case 2664: return fold_fake.automatic;
    case 2383: return fold_fake.status;
    case 2222:
        if (fold_fake.writes < 64) {
            fold_fake.written_lines[fold_fake.writes] = wparam;
            fold_fake.written_levels[fold_fake.writes] = lparam;
        }
        ++fold_fake.writes;
        if (fold_fake.writes == fold_fake.mutate_after_write) fold_fake_mutate();
        return 0;
    default: ++fold_fake.bad_dereference; return 0;
    }
}
