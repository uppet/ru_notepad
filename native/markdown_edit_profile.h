#ifndef RU_MARKDOWN_EDIT_PROFILE_H
#define RU_MARKDOWN_EDIT_PROFILE_H
/* Private edit/Undo cumulative diagnostic, one translation unit only. Never include in a product
 * build. No Ru API, allocation, locks, recovery, document data, or clock calls
 * in the owner hot-counter path. All storage and output are bounded.
 *
 * MPP_CUSTOM_BACKEND supplies MPP_TLS, MPP_ATOMIC, and the mpp_backend_*
 * functions used below; tests exercise this actual header with synthetic clocks.
 * Call mpp_init once on the immutable owner before application work. Call
 * mpp_finalize only on orderly owner exit. Nothing here installs an exit hook.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#include <limits.h>

#ifndef MPP_CUSTOM_BACKEND
# ifndef _WIN32
#  error "Production profile requires Windows; tests must inject MPP_CUSTOM_BACKEND"
# endif
# include <windows.h>
# ifdef _MSC_VER
#  define MPP_TLS __declspec(thread)
# elif defined(__MINGW64__) && defined(__x86_64__) && defined(__GNUC__)
#  define MPP_NATIVE_PE_TLS 1
#  include <intrin.h>
# else
#  error "Unsupported native TLS ABI: do not substitute emulated TLS"
# endif
# define MPP_ATOMIC volatile LONG
static uint32_t mpp_backend_get_last_error(void) { return (uint32_t)GetLastError(); }
static void mpp_backend_set_last_error(uint32_t e) { SetLastError((DWORD)e); }
static uint64_t mpp_backend_thread_id(void) { return (uint64_t)GetCurrentThreadId(); }
static int mpp_backend_claim(MPP_ATOMIC *p) { return InterlockedCompareExchange(p,1,0)==0; }
static void mpp_backend_foreign(MPP_ATOMIC *p) { (void)InterlockedExchange(p,1); }
static int mpp_backend_atomic_read(MPP_ATOMIC *p) { return InterlockedCompareExchange(p,0,0)!=0; }
static int mpp_backend_qpf(int64_t *v) {
    LARGE_INTEGER q; if (!QueryPerformanceFrequency(&q)) return 0;
    *v=(int64_t)q.QuadPart; return 1;
}
static int mpp_backend_qpc(int64_t *v) {
    LARGE_INTEGER q; if (!QueryPerformanceCounter(&q)) return 0;
    *v=(int64_t)q.QuadPart; return 1;
}
static int mpp_backend_cpu(uint64_t *user, uint64_t *kernel) {
    FILETIME c,e,k,u;
    if (!GetThreadTimes(GetCurrentThread(),&c,&e,&k,&u)) return 0;
    *user=((uint64_t)u.dwHighDateTime<<32)|(uint64_t)u.dwLowDateTime;
    *kernel=((uint64_t)k.dwHighDateTime<<32)|(uint64_t)k.dwLowDateTime;
    return 1;
}
static int mpp_backend_write(FILE *f,const char *s,size_t n) {
    return fwrite(s,1,n,f)==n && fflush(f)==0;
}
#endif

#define MPP_PHASE_COUNT 8u
#define MPP_HOT_COUNT 4u
#define MPP_STACK_LIMIT 32u
#define MPP_JSON_LIMIT 49152u
#define MPP_SNAPSHOT_LIMIT 5u

typedef enum {
    MPP_TIMER_ROOT=0, MPP_BRIDGE_ADVANCE=1, MPP_PURE_FEED=2,
    MPP_BRIDGE_PUBLISH=3, MPP_BULK_PREPARE=4, MPP_NATIVE_OTHER=5,
    MPP_NATIVE_BULK=6, MPP_CALLBACK=7
} mpp_phase;
typedef enum {
    MPP_HOT_V_INDEX=0, MPP_HOT_ENV_GET=1, MPP_HOT_HEAP_NEW=2,
    MPP_HOT_V_CALL=3
} mpp_hot;
typedef enum {
    MPP_FAIL_NONE=0, MPP_FAIL_INIT=1, MPP_FAIL_QPF=2, MPP_FAIL_QPC=3,
    MPP_FAIL_CPU=4, MPP_FAIL_CLOCK_REVERSED=5, MPP_FAIL_OVERFLOW=6,
    MPP_FAIL_BAD_PHASE=7, MPP_FAIL_BAD_HOT=8, MPP_FAIL_STACK_OVERFLOW=9,
    MPP_FAIL_TOKEN=10, MPP_FAIL_STACK_UNDERFLOW=11, MPP_FAIL_CHILD_TICKS=12,
    MPP_FAIL_RU_FAIL=13, MPP_FAIL_PANIC=14, MPP_FAIL_TRAP_RESTORE=15,
    MPP_FAIL_TRAP_OOM=16, MPP_FAIL_PROGRESS=17, MPP_FAIL_FOREIGN_THREAD=18,
    MPP_FAIL_INCOMPLETE=19, MPP_FAIL_UNCLOSED=20, MPP_FAIL_PARTITION=21,
    MPP_FAIL_COVERAGE=22, MPP_FAIL_OUTPUT=23
} mpp_failure;
typedef struct { uint64_t serial; unsigned depth,phase; } mpp_token;
typedef struct {
    unsigned phase; uint64_t serial,start_tick,child_ticks;
} mpp_frame;
typedef struct {
    uint64_t entries,inclusive_ticks,exclusive_ticks,hot[MPP_HOT_COUNT];
} mpp_phase_record;
typedef struct {
    uint64_t identity,generation,revision,feed,length,range_count,range_index,range_offset;
    unsigned eof,pending;
} mpp_progress;
typedef struct {
    unsigned initialized,started,frozen,finalized,completion_requested;
    unsigned depth,have_qpc,have_root_end,finalize_ok;
    mpp_failure failure;
    uint64_t owner_thread_id,frequency,serial,last_qpc;
    uint64_t roots,no_step_roots,root_steps,steps,outermost_root_ticks;
    uint64_t root_user_start,root_kernel_start,root_user_100ns,root_kernel_100ns;
    uint64_t previous_root_end,inter_root_gap_ticks,inter_root_gap_max_ticks;
    uint64_t raw_native_other_entries,raw_native_bulk_entries;
    uint64_t hot[MPP_HOT_COUNT];
    uint64_t scan_bytes,revision_feed,active_identity,active_generation,active_revision;
    unsigned revision_bound,revision_complete,snapshot_count;
    mpp_progress progress;
    mpp_phase_record phases[MPP_PHASE_COUNT];
    mpp_frame stack[MPP_STACK_LIMIT];
} mpp_state;
/* Foreign threads may touch ONLY these separate atomic scalars, never mpp. */
static MPP_ATOMIC mpp_claimed;
static MPP_ATOMIC mpp_foreign_invalid;
#if defined(MPP_NATIVE_PE_TLS)
/* GCC MinGW __thread uses allocating __emutls_get_address. Use one loader-owned
 * native PE TLS slot instead. This explicit ABI is restricted to Windows x64.
 * The template remains zero; only the owner's per-thread copy becomes one.
 * Never cache or retain the current-thread TLS address. No TLS API is called.
 * PE linker/CRT symbols and TLS-directory bounds are checked at initialization.
 * Final binary tests verify this template is in the declared TLS span and that
 * mpp_count contains no call instruction or emulated-TLS reference.
 */
extern unsigned long _tls_index;
extern char *_tls_start;
extern char *_tls_end;
extern const IMAGE_TLS_DIRECTORY64 _tls_used;
static unsigned mpp_tls_template __attribute__((section(".tls$MPP"),used,aligned(4)))=0;
static __inline__ __attribute__((always_inline)) unsigned *mpp_tls_slot(void) {
    uintptr_t vector,block;
    /* Explicit Windows x64 current-thread TLS-vector load. The equivalent
     * MinGW __readgsqword intrinsic triggers GCC 14's bogus zero-object bounds
     * diagnostic, so spell the one instruction out without dereferencing a
     * fabricated C pointer. No process/thread handle or foreign TEB is used. */
    __asm__ volatile ("movq %%gs:0x58, %0" : "=r"(vector) : : "memory");
    if (!vector || _tls_index==0xffffffffUL) return NULL;
    block=((const uintptr_t *)vector)[_tls_index];
    if (!block) return NULL;
    return (unsigned *)(block+((uintptr_t)&mpp_tls_template-(uintptr_t)_tls_used.StartAddressOfRawData));
}
static __inline__ __attribute__((always_inline)) unsigned mpp_tls_get(void) {
    const unsigned *slot=mpp_tls_slot(); return slot ? *slot : 0;
}
static int mpp_tls_prepare(void) {
    uintptr_t start=(uintptr_t)_tls_used.StartAddressOfRawData;
    uintptr_t end=(uintptr_t)_tls_used.EndAddressOfRawData,entry=(uintptr_t)&mpp_tls_template;
    return start && _tls_used.AddressOfIndex==(uintptr_t)&_tls_index && entry>=start &&
        end>=entry && end-entry>=sizeof mpp_tls_template && mpp_tls_slot()!=NULL;
}
static void mpp_tls_set_owner(void) { *mpp_tls_slot()=1; }
#else
static MPP_TLS unsigned mpp_tls_owner;
static unsigned mpp_tls_get(void) { return mpp_tls_owner; }
static int mpp_tls_prepare(void) { return 1; }
static void mpp_tls_set_owner(void) { mpp_tls_owner=1; }
#endif
static mpp_state mpp;
static mpp_state mpp_snapshots[MPP_SNAPSHOT_LIMIT];

typedef struct { uint32_t win32; int crt; } mpp_error;
static mpp_error mpp_save_error(void) {
    mpp_error e; e.win32=mpp_backend_get_last_error(); e.crt=errno; return e;
}
static void mpp_restore_error(mpp_error e) { errno=e.crt; mpp_backend_set_last_error(e.win32); }
static void mpp_fail(mpp_failure why) {
    /* Caller has already established owner TLS eligibility. No OS calls. */
    if (mpp.failure==MPP_FAIL_NONE) mpp.failure=why;
}
static int mpp_owner(void) {
    if (mpp_tls_get()) return 1;
    /* Interlocked operations neither inspect ordinary state nor alter errors. */
    mpp_backend_foreign(&mpp_foreign_invalid); return 0;
}
static int mpp_add_ok(uint64_t a,uint64_t b) { return a<=UINT64_MAX-b; }
static int mpp_add(uint64_t *p,uint64_t n) {
    if (!mpp_add_ok(*p,n)) { mpp_fail(MPP_FAIL_OVERFLOW); return 0; }
    *p+=n; return 1;
}
static int mpp_clock(uint64_t *out) {
    mpp_error saved=mpp_save_error(); int64_t now=0; int ok=0;
    if (!mpp_backend_qpc(&now) || now<0) mpp_fail(MPP_FAIL_QPC);
    else if (mpp.have_qpc && (uint64_t)now<mpp.last_qpc) mpp_fail(MPP_FAIL_CLOCK_REVERSED);
    else { *out=(uint64_t)now; mpp.last_qpc=*out; mpp.have_qpc=1; ok=1; }
    mpp_restore_error(saved); return ok;
}
static int mpp_cpu(uint64_t *u,uint64_t *k) {
    mpp_error saved=mpp_save_error(); int ok=mpp_backend_cpu(u,k);
    if (!ok) mpp_fail(MPP_FAIL_CPU);
    mpp_restore_error(saved); return ok;
}
static int mpp_init(void) {
    mpp_error saved=mpp_save_error(); int64_t frequency=0; int ok=0;
    if (!mpp_tls_prepare()) { mpp_backend_foreign(&mpp_foreign_invalid); goto done; }
    if (mpp_tls_get()) { mpp_fail(MPP_FAIL_INIT); goto done; }
    if (!mpp_backend_claim(&mpp_claimed)) {
        mpp_backend_foreign(&mpp_foreign_invalid); goto done;
    }
    mpp_tls_set_owner();
    mpp.owner_thread_id=mpp_backend_thread_id();
    mpp.initialized=1;
    if (!mpp.owner_thread_id) mpp_fail(MPP_FAIL_INIT);
    else if (!mpp_backend_qpf(&frequency) || frequency<=0) mpp_fail(MPP_FAIL_QPF);
    else { mpp.frequency=(uint64_t)frequency; ok=1; }
 done:
    mpp_restore_error(saved); return ok;
}
static int mpp_is_active(void) {
    if (!mpp_owner()) return 0;
    return mpp.initialized && mpp.failure==MPP_FAIL_NONE && !mpp.frozen && !mpp.finalized && mpp.depth!=0;
}
static int mpp_is_complete(void) {
    if (!mpp_owner()) return 0;
    return mpp.revision_complete && mpp.failure==MPP_FAIL_NONE;
}
static mpp_token mpp_begin(mpp_phase phase) {
    mpp_token t={0,0,0}; uint64_t now,u=0,k=0,gap=0; unsigned root;
    if (!mpp_owner()) return t;
    if (!mpp.initialized || mpp.failure!=MPP_FAIL_NONE || mpp.frozen || mpp.finalized) return t;
    if ((unsigned)phase>=MPP_PHASE_COUNT) { mpp_fail(MPP_FAIL_BAD_PHASE); return t; }
    if (!mpp.depth && phase!=MPP_TIMER_ROOT) return t;
    if (mpp.depth>=MPP_STACK_LIMIT) { mpp_fail(MPP_FAIL_STACK_OVERFLOW); return t; }
    if (mpp.serial==UINT64_MAX || mpp.phases[phase].entries==UINT64_MAX) {
        mpp_fail(MPP_FAIL_OVERFLOW); return t;
    }
    root=mpp.depth==0;
    if (root) {
        mpp.started=1;
        if (mpp.roots==UINT64_MAX) { mpp_fail(MPP_FAIL_OVERFLOW); return t; }
        /* CPU bounds slightly enclose the QPC interval: no interior CPU read. */
        if (!mpp_cpu(&u,&k)) return t;
    }
    if (!mpp_clock(&now)) return t;
    if (root && mpp.have_root_end) {
        if (now<mpp.previous_root_end) { mpp_fail(MPP_FAIL_CLOCK_REVERSED); return t; }
        gap=now-mpp.previous_root_end;
        if (!mpp_add_ok(mpp.inter_root_gap_ticks,gap)) { mpp_fail(MPP_FAIL_OVERFLOW); return t; }
    }
    ++mpp.serial; ++mpp.phases[phase].entries;
    t.serial=mpp.serial; t.depth=mpp.depth+1; t.phase=(unsigned)phase;
    mpp.stack[mpp.depth].phase=(unsigned)phase;
    mpp.stack[mpp.depth].serial=t.serial;
    mpp.stack[mpp.depth].start_tick=now;
    mpp.stack[mpp.depth].child_ticks=0;
    ++mpp.depth;
    if (root) {
        ++mpp.roots; mpp.root_steps=0;
        mpp.root_user_start=u; mpp.root_kernel_start=k;
        mpp.inter_root_gap_ticks+=gap;
        if (gap>mpp.inter_root_gap_max_ticks) mpp.inter_root_gap_max_ticks=gap;
    }
    return t;
}
static int mpp_partition_ok(void) {
    uint64_t sum=0; unsigned i;
    for (i=0;i<MPP_PHASE_COUNT;++i) {
        if (!mpp_add_ok(sum,mpp.phases[i].exclusive_ticks)) { mpp_fail(MPP_FAIL_OVERFLOW); return 0; }
        sum+=mpp.phases[i].exclusive_ticks;
    }
    if (sum!=mpp.outermost_root_ticks) { mpp_fail(MPP_FAIL_PARTITION); return 0; }
    return 1;
}
static void mpp_leave(mpp_token t) {
    mpp_frame *f; mpp_phase_record *p; uint64_t now,elapsed,self,u=0,k=0,du=0,dk=0;
    unsigned root;
    if (!mpp_owner()) return;
    if (mpp.failure!=MPP_FAIL_NONE || mpp.frozen || mpp.finalized) return;
    if (!t.serial && !t.depth && !t.phase) return; /* inactive entry's token */
    if (!mpp.depth) { mpp_fail(MPP_FAIL_STACK_UNDERFLOW); return; }
    f=&mpp.stack[mpp.depth-1];
    if (!t.serial || t.depth!=mpp.depth || t.serial!=f->serial || t.phase!=f->phase) {
        mpp_fail(MPP_FAIL_TOKEN); return;
    }
    if (!mpp_clock(&now)) return;
    if (now<f->start_tick) { mpp_fail(MPP_FAIL_CLOCK_REVERSED); return; }
    elapsed=now-f->start_tick;
    if (f->child_ticks>elapsed) { mpp_fail(MPP_FAIL_CHILD_TICKS); return; }
    self=elapsed-f->child_ticks; root=mpp.depth==1;
    if (root) {
        if (f->phase!=MPP_TIMER_ROOT) { mpp_fail(MPP_FAIL_TOKEN); return; }
        if (!mpp_cpu(&u,&k)) return;
        if (u<mpp.root_user_start || k<mpp.root_kernel_start) { mpp_fail(MPP_FAIL_CLOCK_REVERSED); return; }
        du=u-mpp.root_user_start; dk=k-mpp.root_kernel_start;
    }
    p=&mpp.phases[f->phase];
    if (!mpp_add_ok(p->inclusive_ticks,elapsed) || !mpp_add_ok(p->exclusive_ticks,self) ||
        (!root && !mpp_add_ok(mpp.stack[mpp.depth-2].child_ticks,elapsed)) ||
        (root && (!mpp_add_ok(mpp.outermost_root_ticks,elapsed) ||
                  !mpp_add_ok(mpp.root_user_100ns,du) || !mpp_add_ok(mpp.root_kernel_100ns,dk) ||
                  (!mpp.root_steps && mpp.no_step_roots==UINT64_MAX)))) {
        mpp_fail(MPP_FAIL_OVERFLOW); return;
    }
    p->inclusive_ticks+=elapsed; p->exclusive_ticks+=self;
    if (!root) mpp.stack[mpp.depth-2].child_ticks+=elapsed;
    --mpp.depth; /* only the matching normal exit is allowed to pop */
    if (root) {
        mpp.outermost_root_ticks+=elapsed;
        mpp.root_user_100ns+=du; mpp.root_kernel_100ns+=dk;
        mpp.previous_root_end=now; mpp.have_root_end=1;
        if (!mpp.root_steps) ++mpp.no_step_roots;
        if (!mpp_partition_ok()) return;
        if (mpp.completion_requested) {
            if (!mpp.phases[MPP_PURE_FEED].entries || !mpp.phases[MPP_BRIDGE_PUBLISH].entries ||
                !mpp.raw_native_bulk_entries || !mpp.steps) { mpp_fail(MPP_FAIL_COVERAGE); return; }
            if (!mpp.revision_bound || mpp.revision_complete ||
                mpp.progress.identity!=mpp.active_identity ||
                mpp.progress.generation!=mpp.active_generation ||
                mpp.progress.revision!=mpp.active_revision ||
                mpp.progress.feed!=mpp.progress.length || mpp.revision_feed!=mpp.progress.length ||
                !mpp.progress.eof || mpp.progress.pending || mpp.progress.range_count ||
                mpp.progress.range_index || mpp.progress.range_offset ||
                mpp.snapshot_count>=MPP_SNAPSHOT_LIMIT) { mpp_fail(MPP_FAIL_PROGRESS); return; }
            /* Snapshot only after matching normal root leave: no stack reset,
             * no I/O, allocation, or unfreezing after errors. */
            mpp.revision_complete=1; mpp.completion_requested=0;
            ++mpp.snapshot_count;
            mpp_snapshots[mpp.snapshot_count-1]=mpp;
        }
    }
}
static void mpp_count(mpp_hot hot) {
    unsigned phase;
    /* Owner path: TLS + bounded integer operations only. No platform calls,
     * clocks, atomics, string operations, errno access, or allocation. */
    if (!mpp_tls_get()) { mpp_backend_foreign(&mpp_foreign_invalid); return; }
    if (!mpp.depth || mpp.failure!=MPP_FAIL_NONE || mpp.frozen || mpp.finalized) return;
    if ((unsigned)hot>=MPP_HOT_COUNT) { mpp_fail(MPP_FAIL_BAD_HOT); return; }
    phase=mpp.stack[mpp.depth-1].phase;
    if (mpp.hot[hot]==UINT64_MAX || mpp.phases[phase].hot[hot]==UINT64_MAX) {
        mpp_fail(MPP_FAIL_OVERFLOW); return;
    }
    ++mpp.hot[hot]; ++mpp.phases[phase].hot[hot];
}
static void mpp_invalidate(mpp_failure why) {
    mpp_error saved=mpp_save_error();
    if (mpp_owner() && mpp.started && !mpp.frozen && !mpp.finalized)
        mpp_fail(why>MPP_FAIL_NONE && why<=MPP_FAIL_OUTPUT ? why : MPP_FAIL_PROGRESS);
    mpp_restore_error(saved);
}
static void mpp_note_raw_native_entry(int is_bulk) {
    if (!mpp_is_active()) return;
    (void)mpp_add(is_bulk ? &mpp.raw_native_bulk_entries : &mpp.raw_native_other_entries,1);
}
static void mpp_note_step(void) {
    if (!mpp_is_active()) return;
    if (mpp.steps==UINT64_MAX || mpp.root_steps==UINT64_MAX) { mpp_fail(MPP_FAIL_OVERFLOW); return; }
    ++mpp.steps; ++mpp.root_steps;
}
/* Called before and after each unchanged step body. The application creates
 * a fresh identity for each revision; generation stays fixed for this one
 * synthetic document. A replacement while unfinished invalidates the study. */
static void mpp_track_revision(uint64_t identity,uint64_t generation,uint64_t revision,
    uint64_t feed,int64_t length,int after) {
    if (!mpp_is_active()) return;
    if (!identity || (after!=0 && after!=1) ||
        (length!=1000000 && length!=1000001 && !(length==-1 && !after)) ||
        feed>1000001 || (length>=0 && feed>(uint64_t)length)) {
        mpp_fail(MPP_FAIL_PROGRESS); return;
    }
    if (!mpp.revision_bound) {
        if (after || feed) { mpp_fail(MPP_FAIL_PROGRESS); return; }
        mpp.active_identity=identity; mpp.active_generation=generation;
        mpp.active_revision=revision; mpp.revision_bound=1;
    } else if (identity!=mpp.active_identity || generation!=mpp.active_generation || revision!=mpp.active_revision) {
        if (after || !mpp.revision_complete || generation!=mpp.active_generation ||
            identity<=mpp.active_identity || revision<=mpp.active_revision || feed ||
            mpp.snapshot_count>=MPP_SNAPSHOT_LIMIT) { mpp_fail(MPP_FAIL_PROGRESS); return; }
        mpp.active_identity=identity; mpp.active_revision=revision;
        mpp.revision_feed=0; mpp.revision_complete=0;
    }
    if (feed<mpp.revision_feed || (!after && feed!=mpp.revision_feed)) {
        mpp_fail(MPP_FAIL_PROGRESS); return;
    }
    if (after) {
        if (!mpp_add(&mpp.scan_bytes,feed-mpp.revision_feed)) return;
        mpp.revision_feed=feed;
    }
}
/* Caller validates identity and monotonic scenario progress before this call.
 * Numeric observations only: never pass a native/document pointer as identity. */
static void mpp_set_progress(uint64_t identity,uint64_t generation,uint64_t revision,
    uint64_t feed,uint64_t length,uint64_t range_count,uint64_t range_index,
    uint64_t range_offset,int eof,int pending) {
    if (!mpp_is_active()) return;
    if ((eof!=0 && eof!=1) || (pending!=0 && pending!=1)) { mpp_fail(MPP_FAIL_PROGRESS); return; }
    if (mpp.revision_complete &&
        (identity!=mpp.progress.identity || generation!=mpp.progress.generation ||
         revision!=mpp.progress.revision || feed!=mpp.progress.feed || length!=mpp.progress.length ||
         range_count || range_index || range_offset || !eof || pending)) {
        mpp_fail(MPP_FAIL_PROGRESS); return;
    }
    mpp.progress.identity=identity; mpp.progress.generation=generation;
    mpp.progress.revision=revision; mpp.progress.feed=feed; mpp.progress.length=length;
    mpp.progress.range_count=range_count; mpp.progress.range_index=range_index;
    mpp.progress.range_offset=range_offset;
    mpp.progress.eof=(unsigned)eof; mpp.progress.pending=(unsigned)pending;
}
static void mpp_request_completion(void) {
    if (!mpp_owner()) return;
    if (mpp.failure!=MPP_FAIL_NONE || mpp.frozen || mpp.finalized) return;
    if (!mpp.depth) { mpp_fail(MPP_FAIL_PROGRESS); return; }
    if (!mpp.revision_complete) mpp.completion_requested=1; /* snapshot at closed root */
}

/* Fixed scalar-only JSON builder. No printf/locale/allocation or user strings. */
typedef struct { char bytes[MPP_JSON_LIMIT]; size_t used; int ok; } mpp_json;
static void mpp_json_text(mpp_json *b,const char *s) {
    while (*s) {
        if (!b->ok) return;
        if (b->used>=MPP_JSON_LIMIT) { b->ok=0; return; }
        b->bytes[b->used++]=*s++;
    }
}
static void mpp_json_u64(mpp_json *b,uint64_t n) {
    char digits[20]; unsigned used=0;
    do { digits[used++]=(char)('0'+n%10); n/=10; } while (n);
    while (used) {
        if (!b->ok) return;
        if (b->used>=MPP_JSON_LIMIT) { b->ok=0; return; }
        b->bytes[b->used++]=digits[--used];
    }
}
static void mpp_json_field(mpp_json *b,const char *key,uint64_t value) {
    mpp_json_text(b,",\""); mpp_json_text(b,key); mpp_json_text(b,"\":"); mpp_json_u64(b,value);
}
static void mpp_append_record(mpp_json *b,const mpp_state *s,int foreign) {
    static const char *const phase_names[MPP_PHASE_COUNT]={
        "timer_root","bridge_advance","pure_feed","bridge_publish","bulk_prepare",
        "native_other","native_bulk","callback"
    };
    unsigned i,j;
    mpp_json_text(b,"{\"schema\":1,\"snapshot_index\":");
    mpp_json_u64(b,s->snapshot_count);
    mpp_json_field(b,"scan_bytes",s->scan_bytes);
    mpp_json_field(b,"failure_code",(uint64_t)s->failure);
    mpp_json_field(b,"foreign_thread_invalid",(uint64_t)foreign);
    mpp_json_field(b,"started",s->started);
    mpp_json_field(b,"completion_requested",s->completion_requested);
    mpp_json_field(b,"complete",s->revision_complete);
    mpp_json_field(b,"closed",s->depth==0);
    mpp_json_field(b,"depth",s->depth);
    mpp_json_field(b,"qpc_frequency",s->frequency);
    mpp_json_field(b,"root_count",s->roots);
    mpp_json_field(b,"no_step_root_count",s->no_step_roots);
    mpp_json_field(b,"step_count",s->steps);
    mpp_json_field(b,"outermost_root_ticks",s->outermost_root_ticks);
    mpp_json_field(b,"root_user_100ns",s->root_user_100ns);
    mpp_json_field(b,"root_kernel_100ns",s->root_kernel_100ns);
    mpp_json_field(b,"inter_root_gap_ticks",s->inter_root_gap_ticks);
    mpp_json_field(b,"inter_root_gap_max_ticks",s->inter_root_gap_max_ticks);
    mpp_json_field(b,"raw_native_other_entries",s->raw_native_other_entries);
    mpp_json_field(b,"raw_native_bulk_entries",s->raw_native_bulk_entries);
    mpp_json_text(b,",\"progress\":{\"identity\":"); mpp_json_u64(b,s->progress.identity);
    mpp_json_field(b,"generation",s->progress.generation);
    mpp_json_field(b,"revision",s->progress.revision);
    mpp_json_field(b,"feed",s->progress.feed);
    mpp_json_field(b,"length",s->progress.length);
    mpp_json_field(b,"range_count",s->progress.range_count);
    mpp_json_field(b,"range_index",s->progress.range_index);
    mpp_json_field(b,"range_offset",s->progress.range_offset);
    mpp_json_field(b,"eof",s->progress.eof);
    mpp_json_field(b,"pending",s->progress.pending);
    mpp_json_text(b,"}");
    mpp_json_text(b,",\"hot_names\":[\"v_index\",\"env_get\",\"heap_new\",\"v_call\"],\"hot_totals\":[");
    for (j=0;j<MPP_HOT_COUNT;++j) { if (j) mpp_json_text(b,","); mpp_json_u64(b,s->hot[j]); }
    mpp_json_text(b,"],\"phases\":[");
    for (i=0;i<MPP_PHASE_COUNT;++i) {
        if (i) mpp_json_text(b,",");
        mpp_json_text(b,"{\"name\":\""); mpp_json_text(b,phase_names[i]); mpp_json_text(b,"\"");
        mpp_json_field(b,"entries",s->phases[i].entries);
        mpp_json_field(b,"inclusive_ticks",s->phases[i].inclusive_ticks);
        mpp_json_field(b,"exclusive_ticks",s->phases[i].exclusive_ticks);
        mpp_json_text(b,",\"hot\":[");
        for (j=0;j<MPP_HOT_COUNT;++j) { if (j) mpp_json_text(b,","); mpp_json_u64(b,s->phases[i].hot[j]); }
        mpp_json_text(b,"]}");
    }
    mpp_json_text(b,"]}");
}
static int mpp_finalize(FILE *owned_output) {
    mpp_error saved=mpp_save_error(); mpp_json b; unsigned i; int foreign,ok=0;
    if (!mpp_owner()) goto done;
    if (mpp.finalized) { ok=(int)mpp.finalize_ok; goto done; }
    foreign=mpp_backend_atomic_read(&mpp_foreign_invalid);
    if (foreign) mpp_fail(MPP_FAIL_FOREIGN_THREAD);
    if (mpp.depth) mpp_fail(MPP_FAIL_UNCLOSED);
    if (!mpp.revision_complete || mpp.completion_requested ||
        mpp.snapshot_count<4 || mpp.snapshot_count>MPP_SNAPSHOT_LIMIT) mpp_fail(MPP_FAIL_INCOMPLETE);
    if (mpp.failure==MPP_FAIL_NONE) (void)mpp_partition_ok();
    mpp.finalized=1;
    b.used=0; b.ok=1;
    mpp_json_text(&b,"RU_MARKDOWN_EDIT_PROFILE {\"schema\":1,\"record\":\"markdown_edit_profile\","
        "\"diagnostic_only\":true,\"product_acceptance\":\"separate_not_claimed\","
        "\"timing_kind\":\"nested_qpc_wall\",\"cpu_kind\":\"outer_timer_thread_only\","
        "\"sampling\":false,\"whole_process_hotspots\":false,\"valid\":");
    mpp_json_text(&b,mpp.failure==MPP_FAIL_NONE ? "true" : "false");
    mpp_json_text(&b,",\"raw_counts_trusted\":");
    mpp_json_text(&b,mpp.failure==MPP_FAIL_NONE ? "true" : "false");
    mpp_json_field(&b,"failure_code",(uint64_t)mpp.failure);
    mpp_json_field(&b,"snapshot_count",mpp.snapshot_count);
    mpp_json_text(&b,",\"records\":[");
    for (i=0;i<mpp.snapshot_count && i<MPP_SNAPSHOT_LIMIT;++i) {
        if (i) mpp_json_text(&b,",");
        mpp_append_record(&b,&mpp_snapshots[i],foreign);
    }
    mpp_json_text(&b,"],\"final\":"); mpp_append_record(&b,&mpp,foreign);
    mpp_json_text(&b,"}\n");
    if (!b.ok || !owned_output || !mpp_backend_write(owned_output,b.bytes,b.used)) mpp_fail(MPP_FAIL_OUTPUT);
    else if (mpp.failure==MPP_FAIL_NONE) ok=1;
    mpp.finalize_ok=(unsigned)ok;
 done:
    mpp_restore_error(saved); return ok;
}
#endif
