#!/usr/bin/env python3
"""Actual Win32 TLS, errno, LastError and final binary hot-counter controls."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include <string.h>
#include "markdown_edit_profile.h"
#define CHECK(x) do { if (!(x)) return __LINE__; } while (0)
static void seed(void) { errno=EDOM; SetLastError(0x12345678UL); }
static int preserved(void) { DWORD win=GetLastError(); int crt=errno; return win==0x12345678UL && crt==EDOM; }
__attribute__((noinline,used)) void checked_hot_counter(mpp_hot h) { mpp_count(h); }
static void revision(unsigned i, unsigned total) {
    uint64_t len=(i==1 || (i==3 && total==5))?1000001:1000000;
    mpp_token r=mpp_begin(MPP_TIMER_ROOT),t;
    mpp_note_step(); mpp_track_revision(i+1,1,i,0,-1,0);
    t=mpp_begin(MPP_PURE_FEED); checked_hot_counter(MPP_HOT_V_INDEX); mpp_leave(t);
    t=mpp_begin(MPP_BRIDGE_PUBLISH); mpp_count(MPP_HOT_ENV_GET); mpp_leave(t);
    t=mpp_begin(MPP_NATIVE_BULK); mpp_note_raw_native_entry(1); mpp_count(MPP_HOT_HEAP_NEW); mpp_leave(t);
    mpp_track_revision(i+1,1,i,len,(int64_t)len,1);
    mpp_set_progress(i+1,1,i,len,len,0,0,0,1,0); mpp_request_completion(); mpp_leave(r);
}
static DWORD WINAPI foreign(void *unused) {
    mpp_token t; (void)unused; seed();
    t=mpp_begin(MPP_CALLBACK); checked_hot_counter(MPP_HOT_V_INDEX); mpp_leave(t);
    mpp_note_step(); mpp_note_raw_native_entry(1);
    mpp_track_revision(99,1,99,0,-1,0); mpp_invalidate(MPP_FAIL_PANIC);
    return !preserved() || mpp_is_active() || mpp_is_complete();
}
int main(int argc,char **argv) {
    unsigned n=4; HANDLE thread; DWORD code=99; mpp_state before;
    CHECK(argc==2); seed(); CHECK(mpp_init()); CHECK(preserved());
    CHECK(mpp.owner_thread_id==(uint64_t)GetCurrentThreadId());
    if (!strcmp(argv[1],"--foreign")) {
        before=mpp; thread=CreateThread(NULL,0,foreign,NULL,0,NULL); CHECK(thread);
        CHECK(WaitForSingleObject(thread,10000)==WAIT_OBJECT_0);
        CHECK(GetExitCodeThread(thread,&code)); CHECK(CloseHandle(thread)); CHECK(code==0);
        CHECK(!memcmp(&before,&mpp,sizeof mpp)); CHECK(mpp_backend_atomic_read(&mpp_foreign_invalid)==1);
        seed(); CHECK(!mpp_finalize(stdout)); CHECK(preserved());
        CHECK(mpp.failure==MPP_FAIL_FOREIGN_THREAD);
    } else {
        CHECK(!strcmp(argv[1],"--four") || !strcmp(argv[1],"--five"));
        if (!strcmp(argv[1],"--five")) n=5;
        for (unsigned i=0;i<n;i++) { seed(); revision(i,n); CHECK(preserved()); CHECK(mpp.failure==MPP_FAIL_NONE); }
        CHECK(mpp.snapshot_count==n && mpp_is_complete());
        seed(); CHECK(mpp_finalize(stdout)); CHECK(preserved());
        before=mpp; checked_hot_counter(MPP_HOT_V_INDEX); CHECK(!memcmp(&before,&mpp,sizeof mpp));
        CHECK(mpp_finalize(stdout)); CHECK(preserved());
    }
    puts("MARKDOWN_EDIT_WINDOWS_CONTROL_PASS=1"); return 0;
}
'''

def inspect_counter(disassembly):
    def body_for(name):
        match = re.search(r'^[0-9a-f]+ <' + name + r'>:\n(.*?)(?=^[0-9a-f]+ <|\Z)', disassembly, re.M | re.S)
        if not match:
            raise ValueError('Missing counter symbol')
        return match.group(1)
    wrapper = body_for('checked_hot_counter')
    # GCC may inline the header counter or use one direct tail jump to it.
    has_tail = re.search(r'\bjmpq?\s+[^\n]*<mpp_count>', wrapper)
    body = wrapper + (body_for('mpp_count') if has_tail else '')
    if re.search(r'\bcallq?\b|__emutls|__imp_', body):
        raise ValueError('Counter contains a call or emulated/platform TLS access')
    if not re.search(r'%gs:0x58', body):
        raise ValueError('Missing native current-thread TLS access')
    for target in re.findall(r'\bjmpq?\s+[^\n]*<([^>]+)>', body):
        if not re.fullmatch(r'(?:checked_hot_counter|mpp_count)(?:\+0x[0-9a-f]+)?', target):
            raise ValueError('Counter tail-calls another function')
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cc', default='gcc')
    p.add_argument('--objdump', default='objdump')
    a = p.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows required')
    with tempfile.TemporaryDirectory(prefix='mi-edit-native-controls-') as tmp:
        root=Path(tmp); source=root/'control.c'; binary=root/'control.exe'
        source.write_text(HARNESS)
        subprocess.run([a.cc,'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Werror',
                        '-I',str(ROOT/'native'),str(source),'-o',str(binary)],check=True,timeout=60)
        assembly=subprocess.check_output([a.objdump,'-d',str(binary)],text=True,timeout=20)
        inspect_counter(assembly)
        for mode in ('--four','--five','--foreign'):
            subprocess.run([str(binary),mode],check=True,timeout=15)
    print('MARKDOWN_EDIT_WINDOWS_CONTROLS_COMPLETE=1')

if __name__=='__main__': main()
