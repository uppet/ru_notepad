#define RU_MARKDOWN_FOLD_TEST 1
#include "../native/ru_markdown_fold.c"
#include <stdio.h>
#include <stdlib.h>

static unsigned checks;
#define CHECK(test) do { ++checks; if (!(test)) { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #test); exit(1); \
} } while (0)

static FoldPlanStorage plan;
static RuMarkdownFoldResult result;
static uint32_t bytes;
static void *const hwnd = (void *)(uintptr_t)UINT64_C(0x100000001);
static void *const parent = (void *)(uintptr_t)UINT64_C(0x200000002);
static void *const module = (void *)(uintptr_t)UINT64_C(0x300000003);
static void *const opaque = (void *)(uintptr_t)UINT64_C(0x400000004);
static void *const doc = (void *)(uintptr_t)UINT64_C(0x500000005);

static void reset(void) {
    memset(&fold_fake, 0, sizeof(fold_fake));
    fold_fake.hwnd = hwnd; fold_fake.parent = parent; fold_fake.module = module;
    fold_fake.opaque = opaque; fold_fake.doc = doc;
    fold_fake.length = 1000; fold_fake.lines = 100;
    fold_fake.mask = 3; fold_fake.alive = fold_fake.class_ok = fold_fake.export_available = 1;
    fold_fake.current_process = fold_fake.owner_process = 19;
    fold_fake.current_thread = fold_fake.owner_thread = 29;
    fold_fake.parent_process = 19; fold_fake.parent_thread = 29; fold_fake.parent_alive = 1;
    memset(&plan, 0, sizeof(plan));
    memset(&result, 0xa5, sizeof(result));
    plan.header.version = RU_MARKDOWN_FOLD_ABI;
    plan.header.range_count = 1;
    plan.header.expected_lines = 100;
    plan.header.max_lines = 64;
    plan.ranges[0].count = 100;
    plan.ranges[0].depth = 2;
    bytes = 48;
}

static uint32_t run(void) {
    uint32_t status;
    fold_fake.last_error = 0x1234abcd;
    status = ru_markdown_fold_apply_v1(hwnd, parent, module, opaque, doc, 1000,
                                      &plan, bytes, &result, sizeof(result));
    CHECK(fold_fake.last_error == 0x1234abcd);
    CHECK(status == result.status);
    CHECK(result.reserved0 == 0 && result.reserved1 == 0);
    CHECK(result.completed <= result.attempted && result.attempted <= 64);
    CHECK(result.attempted - result.completed <= 1);
    CHECK(result.attempted == fold_fake.writes);
    CHECK(fold_fake.bad_dereference == 0);
    CHECK((status == RU_MARKDOWN_FOLD_NATIVE_ERROR) == (result.scintilla_status != 0));
    return status;
}

static void expect_bad_plan(void) {
    CHECK(run() == RU_MARKDOWN_FOLD_BAD_PLAN);
    CHECK(result.attempted == 0 && result.completed == 0);
    CHECK(result.next_index == 0 && result.next_offset == 0);
    CHECK(fold_fake.direct_calls == 0 && fold_fake.qualifications == 0);
}

static void envelope(const void *input, uint32_t input_bytes,
                      void *output, uint32_t output_bytes) {
    RuMarkdownFoldResult before = result;
    FoldPlanStorage before_plan = plan;
    fold_fake.last_error = 0x1234abcd;
    CHECK(ru_markdown_fold_apply_v1(hwnd, parent, module, opaque, doc, 1000,
          input, input_bytes, output, output_bytes) == RU_MARKDOWN_FOLD_BAD_ARGUMENT);
    CHECK(fold_fake.last_error == 0x1234abcd);
    CHECK(!memcmp(&result, &before, sizeof(result)));
    CHECK(!memcmp(&plan, &before_plan, sizeof(plan)));
    CHECK(fold_fake.direct_calls == 0 && fold_fake.qualifications == 0);
}

static void argument_failure(unsigned which) {
    void *h = hwnd, *p = parent, *m = module, *o = opaque, *d = doc;
    intptr_t length = 1000;
    uint32_t status;
    if (which == 0) h = NULL;
    if (which == 1) p = NULL;
    if (which == 2) m = NULL;
    if (which == 3) o = NULL;
    if (which == 4) d = NULL;
    if (which == 5) length = -1;
    if (which == 6) length = 32000001;
    if (which == 7) length = INTPTR_MAX;
    fold_fake.last_error = 0x1234abcd;
    status = ru_markdown_fold_apply_v1(h, p, m, o, d, length,
                                      &plan, bytes, &result, sizeof(result));
    CHECK(status == RU_MARKDOWN_FOLD_BAD_ARGUMENT && result.status == status);
    CHECK(!result.attempted && !result.completed && !result.next_index && !result.next_offset);
    CHECK(!result.scintilla_status && !result.reserved0 && !result.reserved1);
    CHECK(fold_fake.last_error == 0x1234abcd);
    CHECK(fold_fake.direct_calls == 0 && fold_fake.qualifications == 0);
}

int main(void) {
    uint32_t i, total_qualifications;
    CHECK(sizeof(void *) == 8);
    CHECK(ru_markdown_fold_abi() == 0x10000);
    reset(); CHECK(run() == 0);
    CHECK(result.attempted == 64 && result.completed == 64);
    CHECK(result.next_index == 0 && result.next_offset == 64);
    for (i = 0; i < 64; ++i) {
        CHECK(fold_fake.written_lines[i] == i && fold_fake.written_levels[i] == 1026);
    }
    reset(); plan.header.max_lines = 1; CHECK(run() == 0);
    CHECK(result.attempted == 1 && result.next_offset == 1);
    reset(); plan.header.max_lines = 65; expect_bad_plan();
    reset(); plan.header.max_lines = 0; expect_bad_plan();
    reset(); plan.header.range_offset = 97; CHECK(run() == 0);
    CHECK(result.attempted == 3 && result.next_index == 1 && result.next_offset == 0);
    reset(); plan.header.range_index = 1; CHECK(run() == 0);
    CHECK(result.attempted == 0 && result.next_index == 1);
    reset(); plan.header.range_count = 0; bytes = 32; CHECK(run() == 0);
    CHECK(result.attempted == 0 && result.next_index == 0);

    reset(); plan.header.range_count = 64; bytes = 1056;
    for (i = 0; i < 64; ++i) {
        plan.ranges[i].start = 63-i; plan.ranges[i].count = 1;
        plan.ranges[i].depth = i % 7; plan.ranges[i].header = i % 2;
    }
    CHECK(run() == 0 && result.attempted == 64 && result.next_index == 64);
    for (i = 0; i < 64; ++i) {
        CHECK(fold_fake.written_lines[i] == 63-i);
        CHECK(fold_fake.written_levels[i] == (intptr_t)(1024 + i%7 + (i%2 ? 8192 : 0)));
    }
    reset(); plan.header.range_count = 2; bytes = 64;
    plan.ranges[0].count = 1;
    plan.ranges[1].count = 1; plan.ranges[1].header = 1;
    CHECK(run() == 0 && result.attempted == 2);
    CHECK(fold_fake.written_lines[0] == 0 && fold_fake.written_lines[1] == 0);
    CHECK(fold_fake.written_levels[1] == 9216);

    /* Complete validation catches the final range even outside this batch,
     * and malformed ranges before a valid incoming cursor. */
    reset(); plan.header.range_count = 64; bytes = 1056; plan.header.max_lines = 1;
    for (i = 0; i < 64; ++i) plan.ranges[i].count = 1;
    plan.ranges[63].depth = 7; expect_bad_plan();
    reset(); plan.header.range_count = 2; bytes = 64; plan.header.range_index = 1;
    plan.ranges[0].count = 0; plan.ranges[1].count = 1; expect_bad_plan();
    reset(); plan.header.version++; expect_bad_plan();
    reset(); plan.header.range_count = 65; expect_bad_plan();
    reset(); plan.header.range_count = UINT32_MAX; expect_bad_plan();
    reset(); plan.header.range_count = 0; expect_bad_plan();
    reset(); plan.header.reserved0 = 1; expect_bad_plan();
    reset(); plan.header.reserved1 = 1; expect_bad_plan();
    reset(); plan.header.expected_lines = 0; expect_bad_plan();
    reset(); plan.header.range_index = 2; expect_bad_plan();
    reset(); plan.header.range_index = 1; plan.header.range_offset = 1; expect_bad_plan();
    reset(); plan.header.range_offset = 100; expect_bad_plan();
    reset(); plan.ranges[0].count = 0; expect_bad_plan();
    reset(); plan.ranges[0].depth = 7; expect_bad_plan();
    reset(); plan.ranges[0].header = 2; expect_bad_plan();
    reset(); plan.ranges[0].header = 1; expect_bad_plan();
    reset(); plan.ranges[0].start = 100; expect_bad_plan();
    reset(); plan.ranges[0].start = 1; expect_bad_plan();
    reset(); plan.ranges[0].start = UINT32_MAX; plan.ranges[0].count = 2; expect_bad_plan();
    reset(); plan.ranges[0].start = 1; plan.ranges[0].count = UINT32_MAX; expect_bad_plan();
    reset(); plan.header.expected_lines = UINT32_MAX;
    fold_fake.lines = UINT32_MAX; plan.ranges[0].start = UINT32_MAX-1;
    plan.ranges[0].count = 1; expect_bad_plan();
    reset(); plan.header.expected_lines = 1002; expect_bad_plan();

    reset(); envelope(NULL, bytes, &result, 32);
    reset(); envelope(&plan, bytes, NULL, 32);
    reset(); envelope((const char *)&plan+1, bytes, &result, 32);
    reset(); envelope(&plan, bytes, (char *)&result+1, 32);
    reset(); envelope(&plan, 0, &result, 32);
    reset(); envelope(&plan, 31, &result, 32);
    reset(); envelope(&plan, 33, &result, 32);
    reset(); envelope(&plan, 1072, &result, 32);
    reset(); envelope(&plan, UINT32_MAX, &result, 32);
    reset(); envelope(&plan, bytes, &result, 0);
    reset(); envelope(&plan, bytes, &result, 31);
    reset(); envelope(&plan, bytes, &result, 33);
    reset(); envelope(&plan, bytes, &result, UINT32_MAX);
    reset(); envelope(&plan, bytes, &plan, 32);
    reset(); envelope(&plan, bytes, (char *)&plan+16, 32);
    reset(); envelope((char *)&plan+16, bytes, &plan, 32);
    reset(); envelope((void *)(UINTPTR_MAX-15), 48, &result, 32);
    reset(); envelope(&plan, bytes, (void *)(UINTPTR_MAX-15), 32);
    for (i = 0; i < 8; ++i) { reset(); argument_failure(i); }
    reset(); plan.header.range_offset = 5; fold_fake.doc = (void *)(uintptr_t)0x7777;
    CHECK(run() == RU_MARKDOWN_FOLD_STALE);
    CHECK(!result.attempted && result.next_index == 0 && result.next_offset == 5);

    /* Every prequalification identity error must cause zero direct calls. */
    for (i = 1; i <= FAKE_PARENT_DEAD; ++i) {
        reset(); fold_fake.mutation = i; fold_fake_mutate();
        CHECK(run() == (i == FAKE_STATUS ? RU_MARKDOWN_FOLD_NATIVE_ERROR :
                       (i == FAKE_MASK || i == FAKE_AUTOMATIC) ?
                       RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE : RU_MARKDOWN_FOLD_STALE));
        CHECK(result.attempted == 0);
        if (i == FAKE_DESTROY || i >= FAKE_OPAQUE) CHECK(fold_fake.direct_calls == 0);
    }
    reset(); fold_fake.export_available = 0;
    CHECK(run() == RU_MARKDOWN_FOLD_INELIGIBLE_PREWRITE);
    CHECK(result.attempted == 0 && fold_fake.direct_calls == 0);
    reset(); fold_fake.status = -1;
    CHECK(run() == RU_MARKDOWN_FOLD_NATIVE_ERROR && result.scintilla_status == UINT32_MAX);
    reset(); fold_fake.status = (intptr_t)UINT64_C(0x100000000);
    CHECK(run() == RU_MARKDOWN_FOLD_NATIVE_ERROR && result.scintilla_status == UINT32_MAX);

    /* A postcall failure counts the uncertain write, never silently drops it. */
    for (i = 1; i <= FAKE_PARENT_DEAD; ++i) {
        reset(); fold_fake.mutation = i; fold_fake.mutate_after_write = 2;
        CHECK(run() == (i == FAKE_STATUS ? RU_MARKDOWN_FOLD_NATIVE_ERROR : RU_MARKDOWN_FOLD_STALE));
        CHECK(result.attempted == 2 && result.completed == 1);
        CHECK(result.next_index == 0 && result.next_offset == 2);
    }
    /* Exhaustively inject a native-qualification failure at every boundary
     * of a three-write run: before/after getters, before/after assignments. */
    reset(); plan.header.max_lines = 3; CHECK(run() == 0);
    total_qualifications = fold_fake.qualifications;
    for (i = 1; i <= total_qualifications; ++i) {
        reset(); plan.header.max_lines = 3; fold_fake.fail_qualification = i;
        CHECK(run() == RU_MARKDOWN_FOLD_STALE);
        CHECK(result.next_index == 0 && result.next_offset == result.attempted);
    }
    reset(); plan.header.max_lines = 3; fold_fake.fail_qualification = 39;
    CHECK(run() == RU_MARKDOWN_FOLD_STALE);
    CHECK(result.attempted == 1 && result.completed == 1);
    reset(); plan.header.max_lines = 3; fold_fake.fail_qualification = 27;
    CHECK(run() == RU_MARKDOWN_FOLD_STALE);
    CHECK(result.attempted == 1 && result.completed == 0);
    printf("{\"kind\":\"host_fake_backend\",\"checks\":%u,\"qualification_boundaries\":%u,"
           "\"real_windows_runtime\":false,\"ok\":true}\n", checks, total_qualifications);
    return 0;
}
