/* Actual-header deterministic tests; reset and state fault injection are test-only. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdatomic.h>
#include <pthread.h>
#include <setjmp.h>

#define MPP_CUSTOM_BACKEND 1
#define MPP_TLS _Thread_local
#define MPP_ATOMIC _Atomic unsigned
static _Thread_local uint32_t fake_error;
static _Thread_local uint64_t fake_tid=7;
static int qpf_fail,qpc_fail,cpu_fail,write_fail;
static int64_t fake_frequency=10000000, next_tick=100, tick_stride=10;
static uint64_t next_user=1000,next_kernel=2000,cpu_stride=5;
static unsigned qpf_calls,qpc_calls,cpu_calls,write_calls,thread_calls;
static char emitted[16384]; static size_t emitted_size;
static void clobber(void) { fake_error=0xdeadbeefU; errno=ERANGE; }
static uint32_t mpp_backend_get_last_error(void) { return fake_error; }
static void mpp_backend_set_last_error(uint32_t e) { fake_error=e; }
static uint64_t mpp_backend_thread_id(void) { ++thread_calls; clobber(); return fake_tid; }
static int mpp_backend_claim(MPP_ATOMIC *p) {
    unsigned expected=0; return atomic_compare_exchange_strong(p,&expected,1);
}
static void mpp_backend_foreign(MPP_ATOMIC *p) { atomic_store(p,1); }
static int mpp_backend_atomic_read(MPP_ATOMIC *p) { return atomic_load(p)!=0; }
static int mpp_backend_qpf(int64_t *v) {
    ++qpf_calls; clobber(); *v=fake_frequency; return !qpf_fail;
}
static int mpp_backend_qpc(int64_t *v) {
    ++qpc_calls; clobber(); *v=next_tick; next_tick+=tick_stride; return !qpc_fail;
}
static int mpp_backend_cpu(uint64_t *u,uint64_t *k) {
    ++cpu_calls; clobber(); *u=next_user; *k=next_kernel;
    next_user+=cpu_stride; next_kernel+=cpu_stride; return !cpu_fail;
}
static int mpp_backend_write(FILE *f,const char *s,size_t n) {
    (void)f; ++write_calls; clobber();
    if (write_fail || n>=sizeof emitted) return 0;
    memcpy(emitted,s,n); emitted[n]=0; emitted_size=n; return 1;
}
#include "../native/markdown_phase_profile.h"

static unsigned tests,checks;
#define CHECK(x) do { ++checks; if (!(x)) { \
    fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
#define TEST(name) do { ++tests; name(); } while (0)
static void assert_errors(void) { CHECK(fake_error==0x12345678U); CHECK(errno==EDOM); }
static void reset(void) {
    memset(&mpp,0,sizeof mpp); atomic_store(&mpp_claimed,0); atomic_store(&mpp_foreign_invalid,0);
    mpp_tls_owner=0; fake_tid=7; qpf_fail=qpc_fail=cpu_fail=write_fail=0;
    fake_frequency=10000000; next_tick=100; tick_stride=10;
    next_user=1000; next_kernel=2000; cpu_stride=5;
    qpf_calls=qpc_calls=cpu_calls=write_calls=thread_calls=0;
    emitted[0]=0; emitted_size=0; fake_error=0x12345678U; errno=EDOM;
}
static void init(void) { reset(); CHECK(mpp_init()); assert_errors(); CHECK(qpf_calls==1); }
static void check_stopped(void) {
    mpp_state before=mpp;
    mpp_token t=mpp_begin(MPP_TIMER_ROOT); mpp_leave(t); mpp_count(MPP_HOT_V_INDEX);
    mpp_note_raw_native_entry(1); mpp_note_step(); mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0); mpp_request_completion();
    CHECK(!memcmp(&before,&mpp,sizeof mpp)); assert_errors();
}
static void complete_one_root(void) {
    mpp_token r=mpp_begin(MPP_TIMER_ROOT), t;
    mpp_note_step();
    t=mpp_begin(MPP_PURE_FEED); mpp_count(MPP_HOT_V_INDEX); mpp_leave(t);
    t=mpp_begin(MPP_BRIDGE_PUBLISH); mpp_leave(t);
    t=mpp_begin(MPP_NATIVE_BULK); mpp_note_raw_native_entry(1); mpp_leave(t);
    mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0);
    mpp_request_completion(); CHECK(!mpp_is_complete()); mpp_leave(r); CHECK(mpp_is_complete());
}
static void test_nested_reentrancy(void) {
    mpp_token r,a,n,c,a2,r2; uint64_t sum=0; unsigned i;
    init(); r=mpp_begin(MPP_TIMER_ROOT); /* 100 */
    a=mpp_begin(MPP_BRIDGE_ADVANCE); /* 110 */
    n=mpp_begin(MPP_NATIVE_OTHER); /* 120 */
    c=mpp_begin(MPP_CALLBACK); /* 130 */
    a2=mpp_begin(MPP_BRIDGE_ADVANCE); /* 140 */
    mpp_leave(a2); /* 150 */ mpp_leave(c); /* 160 */
    mpp_leave(n); /* 170 */ mpp_leave(a); /* 180 */
    r2=mpp_begin(MPP_TIMER_ROOT); /* 190 */ mpp_leave(r2); /* 200 */
    mpp_leave(r); /* 210 */
    CHECK(mpp.failure==MPP_FAIL_NONE && mpp.depth==0);
    CHECK(qpc_calls==12 && cpu_calls==2 && mpp.roots==1);
    CHECK(mpp.phases[MPP_TIMER_ROOT].inclusive_ticks==120);
    CHECK(mpp.phases[MPP_TIMER_ROOT].exclusive_ticks==40);
    CHECK(mpp.phases[MPP_BRIDGE_ADVANCE].inclusive_ticks==80);
    CHECK(mpp.phases[MPP_BRIDGE_ADVANCE].exclusive_ticks==30);
    CHECK(mpp.phases[MPP_NATIVE_OTHER].inclusive_ticks==50);
    CHECK(mpp.phases[MPP_NATIVE_OTHER].exclusive_ticks==20);
    CHECK(mpp.phases[MPP_CALLBACK].inclusive_ticks==30);
    CHECK(mpp.phases[MPP_CALLBACK].exclusive_ticks==20);
    CHECK(mpp.outermost_root_ticks==110 && mpp.root_user_100ns==5 && mpp.root_kernel_100ns==5);
    for (i=0;i<MPP_PHASE_COUNT;++i) sum+=mpp.phases[i].exclusive_ticks;
    CHECK(sum==mpp.outermost_root_ticks && mpp.no_step_roots==1);
    assert_errors();
}
static void test_counts_partition(void) {
    unsigned i,j; mpp_token r,t; uint64_t sums[4]={0,0,0,0}; mpp_state before;
    init(); before=mpp;
    for (j=0;j<4;++j) mpp_count((mpp_hot)j);
    CHECK(!memcmp(&before,&mpp,sizeof mpp));
    r=mpp_begin(MPP_TIMER_ROOT);
    for (j=0;j<4;++j) mpp_count((mpp_hot)j);
    t=mpp_begin(MPP_PURE_FEED);
    for (j=0;j<4;++j) { mpp_count((mpp_hot)j); mpp_count((mpp_hot)j); }
    mpp_leave(t); mpp_leave(r);
    for (j=0;j<4;++j) {
        CHECK(mpp.hot[j]==3); CHECK(mpp.phases[0].hot[j]==1); CHECK(mpp.phases[2].hot[j]==2);
        for (i=0;i<8;++i) sums[j]+=mpp.phases[i].hot[j];
        CHECK(sums[j]==mpp.hot[j]);
    }
    CHECK(qpc_calls==4 && cpu_calls==2 && thread_calls==1);
    complete_one_root(); check_stopped(); CHECK(mpp_finalize(stdout)); assert_errors();
    CHECK(write_calls==1 && emitted_size<MPP_JSON_LIMIT);
    CHECK(strstr(emitted,"RU_MARKDOWN_PHASE_PROFILE {\"schema\":1") == emitted);
    CHECK(strstr(emitted,"\"valid\":true") && strstr(emitted,"\"complete\":1") && strstr(emitted,"\"closed\":1"));
    CHECK(mpp_finalize(stdout)); CHECK(write_calls==1); assert_errors();
}
static int body_early(int value) { if (value==0) return 9; if (value==1) return 13; return 21; }
static int wrapper_early(int value) {
    mpp_token t=mpp_begin(MPP_BRIDGE_ADVANCE); int result=body_early(value); mpp_leave(t); return result;
}
static void test_early_returns(void) {
    mpp_token r; init(); r=mpp_begin(MPP_TIMER_ROOT);
    CHECK(wrapper_early(0)==9); CHECK(wrapper_early(1)==13); CHECK(wrapper_early(2)==21);
    mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_NONE && mpp.depth==0);
    CHECK(mpp.phases[MPP_BRIDGE_ADVANCE].entries==3);
}
static void test_token_errors(void) {
    mpp_token r,t,bad;
    init(); r=mpp_begin(MPP_TIMER_ROOT); t=mpp_begin(MPP_PURE_FEED);
    mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_TOKEN && mpp.depth==2); check_stopped();
    init(); r=mpp_begin(MPP_TIMER_ROOT); t=mpp_begin(MPP_PURE_FEED);
    mpp_leave(t); mpp_leave(t); CHECK(mpp.failure==MPP_FAIL_TOKEN && mpp.depth==1); check_stopped();
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_leave(r); mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_STACK_UNDERFLOW && mpp.depth==0); check_stopped();
    init(); r=mpp_begin(MPP_TIMER_ROOT); bad=r; ++bad.serial; mpp_leave(bad);
    CHECK(mpp.failure==MPP_FAIL_TOKEN && mpp.depth==1);
    init(); r=mpp_begin(MPP_TIMER_ROOT); bad=r; bad.phase=MPP_CALLBACK; mpp_leave(bad);
    CHECK(mpp.failure==MPP_FAIL_TOKEN);
    init(); bad.serial=1; bad.depth=1; bad.phase=0; mpp_leave(bad);
    CHECK(mpp.failure==MPP_FAIL_STACK_UNDERFLOW);
    init(); t=mpp_begin(MPP_PURE_FEED); CHECK(t.serial==0 && qpc_calls==0); mpp_leave(t);
    CHECK(mpp.failure==MPP_FAIL_NONE);
}
static void test_depth(void) {
    unsigned i; init();
    for (i=0;i<32;++i) CHECK(mpp_begin(MPP_TIMER_ROOT).serial!=0);
    CHECK(mpp_begin(MPP_CALLBACK).serial==0);
    CHECK(mpp.failure==MPP_FAIL_STACK_OVERFLOW && mpp.depth==32 && cpu_calls==1 && qpc_calls==32);
    check_stopped();
}
static void test_overflows(void) {
    mpp_token r,t;
    init(); mpp.serial=UINT64_MAX; CHECK(!mpp_begin(MPP_TIMER_ROOT).serial); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); mpp.roots=UINT64_MAX; (void)mpp_begin(MPP_TIMER_ROOT); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); mpp.phases[0].entries=UINT64_MAX; (void)mpp_begin(MPP_TIMER_ROOT); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.hot[0]=UINT64_MAX; mpp_count(MPP_HOT_V_INDEX);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.phases[0].hot[0]==0); check_stopped();
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.phases[0].hot[0]=UINT64_MAX; mpp_count(MPP_HOT_V_INDEX);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.hot[0]==0);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.phases[0].inclusive_ticks=UINT64_MAX; mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.depth==1);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.phases[0].exclusive_ticks=UINT64_MAX; mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.depth==1);
    init(); r=mpp_begin(MPP_TIMER_ROOT); t=mpp_begin(MPP_CALLBACK); mpp.stack[0].child_ticks=UINT64_MAX;
    mpp_leave(t); CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.depth==2);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.outermost_root_ticks=UINT64_MAX; mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW && mpp.depth==1);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.root_user_100ns=UINT64_MAX; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.root_kernel_100ns=UINT64_MAX; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.no_step_roots=UINT64_MAX; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.steps=UINT64_MAX; mpp_note_step(); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.root_steps=UINT64_MAX; mpp_note_step(); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.raw_native_bulk_entries=UINT64_MAX; mpp_note_raw_native_entry(1);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.raw_native_other_entries=UINT64_MAX; mpp_note_raw_native_entry(0);
    CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_leave(r); mpp.inter_root_gap_ticks=UINT64_MAX;
    (void)mpp_begin(MPP_TIMER_ROOT); CHECK(mpp.failure==MPP_FAIL_OVERFLOW);
}
static void test_clocks_and_errors(void) {
    mpp_token r,t;
    reset(); qpf_fail=1; CHECK(!mpp_init()); CHECK(mpp.failure==MPP_FAIL_QPF); assert_errors();
    reset(); fake_frequency=0; CHECK(!mpp_init()); CHECK(mpp.failure==MPP_FAIL_QPF); assert_errors();
    reset(); fake_frequency=-1; CHECK(!mpp_init()); CHECK(mpp.failure==MPP_FAIL_QPF); assert_errors();
    reset(); fake_tid=0; CHECK(!mpp_init()); CHECK(mpp.failure==MPP_FAIL_INIT); assert_errors();
    init(); CHECK(!mpp_init()); CHECK(mpp.failure==MPP_FAIL_INIT); assert_errors();
    init(); qpc_fail=1; r=mpp_begin(MPP_TIMER_ROOT); CHECK(!r.serial && mpp.failure==MPP_FAIL_QPC); assert_errors();
    init(); cpu_fail=1; r=mpp_begin(MPP_TIMER_ROOT); CHECK(!r.serial && mpp.failure==MPP_FAIL_CPU && qpc_calls==0); assert_errors();
    init(); next_tick=-1; (void)mpp_begin(MPP_TIMER_ROOT); CHECK(mpp.failure==MPP_FAIL_QPC); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); next_tick=99; (void)mpp_begin(MPP_CALLBACK);
    CHECK(mpp.failure==MPP_FAIL_CLOCK_REVERSED && mpp.depth==1); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); qpc_fail=1; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_QPC && mpp.depth==1); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); cpu_fail=1; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_CPU && mpp.depth==1); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); next_user=0; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_CLOCK_REVERSED); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); next_kernel=0; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_CLOCK_REVERSED); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.stack[0].child_ticks=11; mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_CHILD_TICKS && mpp.depth==1); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); t=mpp_begin(MPP_CALLBACK); next_tick=115; mpp_leave(t);
    CHECK(mpp.failure==MPP_FAIL_NONE); next_tick=114; mpp_leave(r); CHECK(mpp.failure==MPP_FAIL_CLOCK_REVERSED); assert_errors();
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_invalidate(MPP_FAIL_PANIC); assert_errors();
    CHECK(!mpp_finalize(stdout)); assert_errors(); CHECK(strstr(emitted,"\"raw_counts_trusted\":false"));
    init(); complete_one_root(); write_fail=1; CHECK(!mpp_finalize(stdout)); assert_errors();
    CHECK(mpp.failure==MPP_FAIL_OUTPUT && write_calls==1); CHECK(!mpp_finalize(stdout)); CHECK(write_calls==1); assert_errors();
}
static void *foreign_thread(void *arg) {
    mpp_token t; (void)arg; fake_tid=91; fake_error=0x12345678U; errno=EDOM;
    t=mpp_begin(MPP_CALLBACK); mpp_leave(t); mpp_count(MPP_HOT_V_INDEX);
    mpp_note_step(); mpp_note_raw_native_entry(1); mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0); mpp_request_completion();
    mpp_invalidate(MPP_FAIL_PANIC); CHECK(!mpp_is_active()); CHECK(!mpp_is_complete());
    CHECK(!mpp_finalize(stdout)); CHECK(!mpp_init()); assert_errors(); return NULL;
}
static void test_foreign_thread(void) {
    pthread_t thread; mpp_state before; mpp_token r;
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_count(MPP_HOT_ENV_GET); before=mpp;
    CHECK(pthread_create(&thread,NULL,foreign_thread,NULL)==0); CHECK(pthread_join(thread,NULL)==0);
    CHECK(!memcmp(&before,&mpp,sizeof mpp)); CHECK(atomic_load(&mpp_foreign_invalid)==1);
    mpp_leave(r); complete_one_root(); CHECK(!mpp_finalize(stdout));
    CHECK(mpp.failure==MPP_FAIL_FOREIGN_THREAD && strstr(emitted,"\"foreign_thread_invalid\":1")); assert_errors();
}
static void jumped_body(jmp_buf destination,mpp_failure why) {
    (void)mpp_begin(MPP_PURE_FEED); mpp_count(MPP_HOT_HEAP_NEW);
    mpp_invalidate(why); longjmp(destination,17);
}
static void run_longjmp_case(mpp_failure reason) {
    jmp_buf trap; int outcome; mpp_token root,callback; unsigned expected_depth;
    init(); root=mpp_begin(MPP_TIMER_ROOT);
    /* Initialized before setjmp, never changed after: safe on longjmp. */
    callback=mpp_begin(MPP_CALLBACK); expected_depth=mpp.depth+1;
    outcome=setjmp(trap);
    if (!outcome) jumped_body(trap,reason);
    CHECK(outcome==17); CHECK(mpp.failure==reason && mpp.depth==expected_depth);
    mpp_leave(callback); mpp_leave(root); /* no repair or unwind */
    CHECK(mpp.depth==expected_depth); check_stopped();
    CHECK(!mpp_finalize(stdout)); CHECK(strstr(emitted,"\"valid\":false"));
    CHECK(strstr(emitted,"\"closed\":0")); CHECK(strstr(emitted,"\"raw_counts_trusted\":false"));
    assert_errors();
}
static void test_longjmp_recovery(void) {
    run_longjmp_case(MPP_FAIL_TRAP_RESTORE);
    run_longjmp_case(MPP_FAIL_RU_FAIL);
    run_longjmp_case(MPP_FAIL_PANIC);
    run_longjmp_case(MPP_FAIL_TRAP_OOM);
}
/* Model the two application error routes, normal trap-OOM early return and
 * an error rescued inside the selected body. Profiling must not change result. */
static int application_recovery_case(unsigned pattern,int observe) {
    jmp_buf destination; int jump_result;
    const volatile mpp_token root=observe ? mpp_begin(MPP_TIMER_ROOT) : (mpp_token){0,0,0};
    const volatile mpp_token callback=observe ? mpp_begin(MPP_CALLBACK) : (mpp_token){0,0,0};
    jump_result=setjmp(destination);
    if (!jump_result) {
        if (pattern==2) { /* failed rn_trap_new branch, ordinary return */
            if (observe) mpp_invalidate(MPP_FAIL_TRAP_OOM);
            if (observe) { mpp_leave(callback); mpp_leave(root); }
            return 31;
        }
        if (observe) (void)mpp_begin(MPP_PURE_FEED);
        if (pattern==0) { /* normal callback error restores trap then jumps */
            if (observe) mpp_invalidate(MPP_FAIL_TRAP_RESTORE);
            longjmp(destination,41);
        }
        if (pattern==1) { /* failure-action throw goes straight to panic route */
            if (observe) mpp_invalidate(MPP_FAIL_PANIC);
            longjmp(destination,43);
        }
        /* Ru failure is caught; caller still returns an ordinary value. */
        if (observe) mpp_invalidate(MPP_FAIL_RU_FAIL);
        longjmp(destination,47);
    }
    if (observe) { mpp_leave(callback); mpp_leave(root); }
    return jump_result+1;
}
static void test_application_recovery_outcomes(void) {
    unsigned i; int baseline,observed;
    for (i=0;i<4;++i) {
        baseline=application_recovery_case(i,0);
        init(); observed=application_recovery_case(i,1);
        CHECK(observed==baseline); CHECK(mpp.depth==(i==2 ? 2u : 3u));
        CHECK(mpp.failure!=MPP_FAIL_NONE); check_stopped(); CHECK(!mpp_finalize(stdout));
    }
}
static void test_invalidity_and_completion(void) {
    mpp_token r; mpp_state before;
    init(); mpp_invalidate(MPP_FAIL_RU_FAIL); CHECK(mpp.failure==MPP_FAIL_NONE);
    r=mpp_begin(MPP_TIMER_ROOT); mpp_leave(r); mpp_invalidate(MPP_FAIL_PANIC);
    CHECK(mpp.failure==MPP_FAIL_PANIC); before=mpp; mpp_invalidate(MPP_FAIL_RU_FAIL);
    CHECK(!memcmp(&before,&mpp,sizeof mpp));
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_request_completion(); mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_COVERAGE && !mpp.frozen && !mpp.depth);
    init(); mpp_request_completion(); CHECK(mpp.failure==MPP_FAIL_PROGRESS);
    init(); CHECK(!mpp_finalize(stdout)); CHECK(mpp.failure==MPP_FAIL_INCOMPLETE);
    init(); r=mpp_begin(MPP_TIMER_ROOT); CHECK(!mpp_finalize(stdout)); CHECK(mpp.failure==MPP_FAIL_UNCLOSED);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp.phases[1].exclusive_ticks=1; mpp_leave(r);
    CHECK(mpp.failure==MPP_FAIL_PARTITION);
    init(); (void)mpp_begin((mpp_phase)9); CHECK(mpp.failure==MPP_FAIL_BAD_PHASE);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_count((mpp_hot)4); CHECK(mpp.failure==MPP_FAIL_BAD_HOT);
    init(); complete_one_root(); before=mpp; mpp_invalidate(MPP_FAIL_PANIC);
    CHECK(!memcmp(&before,&mpp,sizeof mpp)); CHECK(mpp_finalize(stdout));
}
static void test_multiple_roots_gaps(void) {
    mpp_token r;
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_leave(r); /* 100..110 */
    next_tick=1000; r=mpp_begin(MPP_TIMER_ROOT); mpp_note_step(); mpp_leave(r); /* 1000..1010 */
    next_tick=1100; complete_one_root();
    CHECK(mpp.roots==3 && mpp.no_step_roots==1 && mpp.steps==2 && cpu_calls==6);
    CHECK(mpp.inter_root_gap_ticks==980 && mpp.inter_root_gap_max_ticks==890);
    CHECK(mpp.outermost_root_ticks==90); CHECK(mpp_finalize(stdout));
}
static void test_progress_and_output_edges(void) {
    mpp_state before; mpp_token r; mpp_json b;
    init(); before=mpp; mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0);
    CHECK(!memcmp(&before,&mpp,sizeof mpp));
    r=mpp_begin(MPP_TIMER_ROOT); mpp_set_progress(19,23,29,333,444,4,2,17,0,1);
    CHECK(mpp.progress.identity==19 && mpp.progress.generation==23 && mpp.progress.revision==29);
    CHECK(mpp.progress.feed==333 && mpp.progress.length==444 && mpp.progress.range_count==4);
    CHECK(mpp.progress.range_index==2 && mpp.progress.range_offset==17 && mpp.progress.eof==0 && mpp.progress.pending==1);
    mpp_leave(r); before=mpp; mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0);
    CHECK(!memcmp(&before,&mpp,sizeof mpp));
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_set_progress(1,1,1,0,0,0,0,0,2,0);
    CHECK(mpp.failure==MPP_FAIL_PROGRESS && !mpp.progress.identity);
    init(); r=mpp_begin(MPP_TIMER_ROOT); mpp_set_progress(1,1,1,0,0,0,0,0,0,-1);
    CHECK(mpp.failure==MPP_FAIL_PROGRESS && !mpp.progress.identity);
    init(); complete_one_root(); CHECK(!mpp_finalize(NULL)); CHECK(mpp.failure==MPP_FAIL_OUTPUT && write_calls==0); assert_errors();
    b.used=MPP_JSON_LIMIT; b.ok=1; mpp_json_text(&b,"x"); CHECK(!b.ok && b.used==MPP_JSON_LIMIT);
    b.used=MPP_JSON_LIMIT; b.ok=1; mpp_json_u64(&b,1); CHECK(!b.ok && b.used==MPP_JSON_LIMIT);
    b.used=0; b.ok=1; mpp_json_u64(&b,UINT64_MAX); CHECK(b.ok && b.used==20);
}
static void test_json_worst_case(void) {
    unsigned i,j;
    init(); complete_one_root(); mpp.failure=MPP_FAIL_PROGRESS;
    mpp.hot[0]=mpp.hot[1]=mpp.hot[2]=mpp.hot[3]=UINT64_MAX;
    for (i=0;i<8;++i) {
        mpp.phases[i].entries=mpp.phases[i].inclusive_ticks=mpp.phases[i].exclusive_ticks=UINT64_MAX;
        for (j=0;j<4;++j) mpp.phases[i].hot[j]=UINT64_MAX;
    }
    CHECK(!mpp_finalize(stdout)); CHECK(emitted_size<MPP_JSON_LIMIT);
    CHECK(emitted[emitted_size-1]=='\n'); CHECK(strstr(emitted,"18446744073709551615"));
}
int main(int argc,char **argv) {
    if (argc==2 && !strcmp(argv[1],"--emit-valid")) {
        init(); complete_one_root(); CHECK(mpp_finalize(stdout)); fputs(emitted,stdout); return 0;
    }
    TEST(test_nested_reentrancy); TEST(test_counts_partition); TEST(test_early_returns);
    TEST(test_token_errors); TEST(test_depth); TEST(test_overflows); TEST(test_clocks_and_errors);
    TEST(test_foreign_thread); TEST(test_longjmp_recovery); TEST(test_application_recovery_outcomes); TEST(test_invalidity_and_completion);
    TEST(test_multiple_roots_gaps); TEST(test_progress_and_output_edges); TEST(test_json_worst_case);
    printf("PASS: %u test groups, %u assertions\n",tests,checks); return 0;
}
