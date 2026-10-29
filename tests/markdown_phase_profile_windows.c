/* Actual Win32 loader/TLS/error-state controls. Run --normal and --foreign in
 * separate fresh processes before any GUI study. Never attach to an app. */
#include <string.h>
#include "../native/markdown_phase_profile.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"MPP_WINDOWS_CONTROL FAIL line %u: %s\n",(unsigned)__LINE__,#x); return 1; } } while (0)
static void seed_errors(void) { errno=EDOM; SetLastError(0x12345678UL); }
static int preserved(void) { DWORD win=GetLastError(); int crt=errno; return win==0x12345678UL && crt==EDOM; }
static void finish_valid_root(void) {
    mpp_token t;
    mpp_note_step();
    t=mpp_begin(MPP_PURE_FEED); mpp_count(MPP_HOT_V_INDEX); mpp_leave(t);
    t=mpp_begin(MPP_BRIDGE_PUBLISH); mpp_count(MPP_HOT_ENV_GET); mpp_leave(t);
    t=mpp_begin(MPP_NATIVE_BULK); mpp_note_raw_native_entry(1); mpp_count(MPP_HOT_HEAP_NEW); mpp_leave(t);
    mpp_set_progress(1,1,1,1000000,1000000,0,0,0,1,0); mpp_request_completion();
}
static DWORD WINAPI foreign_control(void *unused) {
    mpp_token t; (void)unused;
    seed_errors();
    t=mpp_begin(MPP_CALLBACK); mpp_count(MPP_HOT_V_INDEX); mpp_leave(t);
    mpp_note_step(); mpp_note_raw_native_entry(1);
    mpp_set_progress(7,7,7,1,1,0,0,0,1,0); mpp_request_completion();
    mpp_invalidate(MPP_FAIL_PANIC);
    if (mpp_is_active() || mpp_is_complete() || !preserved()) return 9;
    return 0;
}
static int run_normal(void) {
    mpp_token root; mpp_state frozen;
    seed_errors(); CHECK(mpp_init()); CHECK(preserved());
    CHECK(mpp.owner_thread_id==(uint64_t)GetCurrentThreadId()); CHECK(preserved());
    root=mpp_begin(MPP_TIMER_ROOT); mpp_count(MPP_HOT_V_CALL); CHECK(preserved());
    finish_valid_root(); CHECK(preserved()); CHECK(!mpp_is_complete());
    mpp_leave(root); CHECK(preserved()); CHECK(mpp_is_complete());
    frozen=mpp; mpp_count(MPP_HOT_V_INDEX); CHECK(!memcmp(&frozen,&mpp,sizeof mpp));
    CHECK(mpp_finalize(stdout)); CHECK(preserved()); CHECK(mpp.failure==MPP_FAIL_NONE);
    CHECK(mpp.frozen && !mpp.depth && mpp.phases[MPP_TIMER_ROOT].entries==1);
    CHECK(mpp_finalize(stdout)); CHECK(preserved());
    puts("MPP_WINDOWS_CONTROL normal PASS"); return 0;
}
static int run_foreign(void) {
    mpp_token root; mpp_state before; HANDLE thread; DWORD waited,code=99;
    seed_errors(); CHECK(mpp_init()); CHECK(preserved());
    root=mpp_begin(MPP_TIMER_ROOT); mpp_count(MPP_HOT_V_CALL); CHECK(preserved());
    before=mpp;
    thread=CreateThread(NULL,0,foreign_control,NULL,0,NULL); CHECK(thread!=NULL);
    waited=WaitForSingleObject(thread,10000); CHECK(waited==WAIT_OBJECT_0);
    CHECK(GetExitCodeThread(thread,&code)); CHECK(CloseHandle(thread)); CHECK(code==0);
    CHECK(!memcmp(&before,&mpp,sizeof mpp)); CHECK(mpp_backend_atomic_read(&mpp_foreign_invalid)==1);
    seed_errors(); finish_valid_root(); mpp_leave(root); CHECK(preserved());
    CHECK(!mpp_finalize(stdout)); CHECK(preserved());
    CHECK(mpp.failure==MPP_FAIL_FOREIGN_THREAD && mpp.frozen && !mpp.depth);
    puts("MPP_WINDOWS_CONTROL foreign PASS"); return 0;
}
int main(int argc,char **argv) {
    if (argc!=2) return 64;
    if (!strcmp(argv[1],"--normal")) return run_normal();
    if (!strcmp(argv[1],"--foreign")) return run_foreign();
    return 64;
}
