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
static char emitted[65536]; static size_t emitted_size;
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
#include "../native/markdown_edit_profile.h"

static unsigned tests,checks;
#define CHECK(x) do { ++checks; if (!(x)) { \
    fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); } } while (0)
#define TEST(name) do { ++tests; name(); } while (0)
static void assert_errors(void) { CHECK(fake_error==0x12345678U); CHECK(errno==EDOM); }
static void reset(void) {
    memset(&mpp,0,sizeof mpp); memset(mpp_snapshots,0,sizeof mpp_snapshots); atomic_store(&mpp_claimed,0); atomic_store(&mpp_foreign_invalid,0);
    mpp_tls_owner=0; fake_tid=7; qpf_fail=qpc_fail=cpu_fail=write_fail=0;
    fake_frequency=10000000; next_tick=100; tick_stride=10;
    next_user=1000; next_kernel=2000; cpu_stride=5;
    qpf_calls=qpc_calls=cpu_calls=write_calls=thread_calls=0;
    emitted[0]=0; emitted_size=0; fake_error=0x12345678U; errno=EDOM;
}
static void init(void) { reset(); CHECK(mpp_init()); assert_errors(); CHECK(qpf_calls==1); }

static void revision(uint64_t id,uint64_t rev,uint64_t len) {
    mpp_token r=mpp_begin(MPP_TIMER_ROOT),t;
    mpp_note_step(); mpp_track_revision(id,1,rev,0,-1,0);
    t=mpp_begin(MPP_PURE_FEED); mpp_count(MPP_HOT_V_INDEX); mpp_leave(t);
    t=mpp_begin(MPP_BRIDGE_PUBLISH); mpp_count(MPP_HOT_ENV_GET); mpp_leave(t);
    t=mpp_begin(MPP_NATIVE_BULK); mpp_note_raw_native_entry(1); mpp_count(MPP_HOT_HEAP_NEW);mpp_leave(t);
    mpp_track_revision(id,1,rev,len,(int64_t)len,1);
    mpp_set_progress(id,1,rev,len,len,0,0,0,1,0);
    mpp_request_completion();CHECK(mpp.depth==1);mpp_leave(r);
}
static void scenario(unsigned n) {
    unsigned i;init();
    for(i=0;i<n;i++) revision(i+1,i,(i==1 || (i==3 && n==5))?1000001:1000000);
}
static void test_good(void) {
    unsigned n,i;uint64_t bytes;
    for(n=4;n<=5;n++) {
        scenario(n);CHECK(mpp.failure==MPP_FAIL_NONE);CHECK(mpp.snapshot_count==n);
        CHECK(!mpp.frozen && mpp.depth==0 && mpp_is_complete());
        bytes=0;
        for(i=0;i<n;i++) {
            const mpp_state *s=&mpp_snapshots[i];bytes+=s->progress.length;
            CHECK(s->snapshot_count==i+1);CHECK(s->scan_bytes==bytes);CHECK(s->depth==0);
            CHECK(s->active_revision==i && s->active_identity==i+1);
        }
        CHECK(mpp_finalize(stdout));assert_errors();CHECK(emitted_size<49152);
        CHECK(strstr(emitted,"RU_MARKDOWN_EDIT_PROFILE ")==emitted);
        CHECK(strstr(emitted,"\"valid\":true")!=NULL);CHECK(strstr(emitted,"\"records\":[")!=NULL);
        CHECK(mpp_finalize(stdout));
    }
}
static void test_duplicate_complete(void) {
    mpp_token r;scenario(4);r=mpp_begin(MPP_TIMER_ROOT);mpp_note_step();
    mpp_track_revision(4,1,3,1000000,1000000,0);mpp_track_revision(4,1,3,1000000,1000000,1);
    mpp_request_completion();mpp_leave(r);CHECK(mpp.snapshot_count==4);CHECK(mpp.scan_bytes==4000001);
    CHECK(mpp_finalize(stdout));
}
static void test_completed_reopened(void) {
    mpp_token r; scenario(4);r=mpp_begin(MPP_TIMER_ROOT);
    mpp_set_progress(4,1,3,1000000,1000000,0,0,0,0,1);
    CHECK(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);CHECK(mpp.depth==1);
    CHECK(!mpp_finalize(stdout));CHECK(mpp.snapshot_count==4);
}
static void test_bad_transitions(void) {
    unsigned kind;
    for(kind=0;kind<5;kind++) {
        mpp_token r;scenario(4);r=mpp_begin(MPP_TIMER_ROOT);
        if(kind==0)mpp_track_revision(3,1,4,0,-1,0);
        if(kind==1)mpp_track_revision(5,1,2,0,-1,0);
        if(kind==2)mpp_track_revision(5,2,4,0,-1,0);
        if(kind==3)mpp_track_revision(5,1,4,1,-1,0);
        if(kind==4)mpp_track_revision(5,1,4,0,-1,1);
        CHECK(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);CHECK(!mpp_finalize(stdout));
        CHECK(strstr(emitted,"\"valid\":false")!=NULL);
    }
}
static void test_unfinished_and_limit(void) {
    mpp_token r;scenario(3);CHECK(!mpp_finalize(stdout));CHECK(mpp.failure==MPP_FAIL_INCOMPLETE);
    scenario(5);revision(6,5,1000000);CHECK(mpp.failure==MPP_FAIL_PROGRESS);CHECK(mpp.snapshot_count==5);
    init();r=mpp_begin(MPP_TIMER_ROOT);mpp_track_revision(1,1,0,0,-1,0);
    mpp_track_revision(2,1,1,0,-1,0);CHECK(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);
    scenario(4);r=mpp_begin(MPP_TIMER_ROOT);mpp_track_revision(5,1,4,0,-1,0);mpp_leave(r);
    CHECK(!mpp_finalize(stdout));CHECK(mpp.failure==MPP_FAIL_INCOMPLETE);
}
static void test_feed_bounds(void) {
    mpp_token r;init();r=mpp_begin(MPP_TIMER_ROOT);mpp_track_revision(1,1,0,0,-1,0);
    mpp_track_revision(1,1,0,1024,1000000,1);CHECK(mpp.scan_bytes==1024);
    mpp_track_revision(1,1,0,1024,1000000,0);mpp_track_revision(1,1,0,1025,1000000,1);CHECK(mpp.scan_bytes==1025);
    mpp_track_revision(1,1,0,1000,1000000,1);CHECK(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);
    init();r=mpp_begin(MPP_TIMER_ROOT);mpp_track_revision(1,1,0,0,999999,0);CHECK(mpp.failure==MPP_FAIL_PROGRESS);mpp_leave(r);
    init();r=mpp_begin(MPP_TIMER_ROOT);mpp_track_revision(1,1,0,0,-1,0);mpp.scan_bytes=UINT64_MAX;
    mpp_track_revision(1,1,0,1,1000000,1);CHECK(mpp.failure==MPP_FAIL_OVERFLOW);mpp_leave(r);
}
static void test_nested_and_errors(void) {
    mpp_token r,a,c;scenario(4);r=mpp_begin(MPP_TIMER_ROOT);a=mpp_begin(MPP_NATIVE_OTHER);c=mpp_begin(MPP_CALLBACK);
    mpp_count(MPP_HOT_V_CALL);mpp_leave(c);mpp_leave(a);mpp_leave(r);CHECK(mpp_partition_ok());CHECK(mpp_finalize(stdout));assert_errors();
    scenario(4);r=mpp_begin(MPP_TIMER_ROOT);mpp_invalidate(MPP_FAIL_PANIC);mpp_leave(r);
    CHECK(mpp.depth==1 && mpp.failure==MPP_FAIL_PANIC);CHECK(!mpp_finalize(stdout));
    scenario(4);r=mpp_begin(MPP_TIMER_ROOT);a=mpp_begin(MPP_NATIVE_OTHER);mpp_leave(r);CHECK(mpp.failure==MPP_FAIL_TOKEN);mpp_leave(a);CHECK(mpp.depth==2);CHECK(!mpp_finalize(stdout));
}
static void *foreign(void *unused) {
    mpp_token t;(void)unused;mpp_tls_owner=0;t=mpp_begin(MPP_CALLBACK);mpp_count(MPP_HOT_V_CALL);mpp_leave(t);return NULL;
}
static void test_foreign_and_output(void) {
    pthread_t thread;mpp_state before;scenario(4);before=mpp;CHECK(!pthread_create(&thread,NULL,foreign,NULL));CHECK(!pthread_join(thread,NULL));
    CHECK(!memcmp(&mpp,&before,sizeof mpp));CHECK(!mpp_finalize(stdout));CHECK(mpp.failure==MPP_FAIL_FOREIGN_THREAD);
    scenario(4);write_fail=1;CHECK(!mpp_finalize(stdout));CHECK(mpp.failure==MPP_FAIL_OUTPUT);
}
int main(int argc,char **argv) {
    if(argc==2 && !strcmp(argv[1],"--emit-valid")) { scenario(5);CHECK(mpp_finalize(stdout));fputs(emitted,stdout);return 0; }
    TEST(test_completed_reopened); TEST(test_good);TEST(test_duplicate_complete);TEST(test_bad_transitions);TEST(test_unfinished_and_limit);
    TEST(test_feed_bounds);TEST(test_nested_and_errors);TEST(test_foreign_and_output);
    printf("PASS: %u edit profile groups, %u assertions\n",tests,checks);return 0;
}
