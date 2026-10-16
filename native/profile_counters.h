#ifndef RU_SYNTAX_PROFILE_COUNTERS_H
#define RU_SYNTAX_PROFILE_COUNTERS_H
/* Private benchmark instrumentation. Never included by a product build.
 * Integer-only recording preserves LastError/errno without calling the OS.
 * Clock and output helpers explicitly save and restore them. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#ifndef RP_LEVEL
#define RP_LEVEL 0
#endif
#ifndef RP_PATH
#define RP_PATH "unknown"
#endif
#ifndef RP_MODE
#define RP_MODE "full"
#endif
#ifndef RP_NATIVE_STYLE_TRACE
#define RP_NATIVE_STYLE_TRACE 0
#endif
#define RP_CORPUS_SHA "ecf8dca884444a5e54e1f40dc6af01cf5e7830ed6fe902d3adf6fdf255f9b3fa"
#define RP_PHASES 5
#define RP_DEPTH 32
#define RP_CALLBACK_DEPTH 8
#define RP_CALIBRATION_PAIRS 128
#if defined(_WIN32)
#include <windows.h>
typedef struct { DWORD win32; int crt; } RpError;
static RpError rp_save_error(void) { RpError e; e.win32=GetLastError(); e.crt=errno; return e; }
static void rp_restore_error(RpError e) { errno=e.crt; SetLastError(e.win32); }
#define RP_SAVE_ERROR() rp_save_error()
#define RP_RESTORE_ERROR(e) rp_restore_error(e)
#else
#include <time.h>
typedef int RpError;
#define RP_SAVE_ERROR() errno
#define RP_RESTORE_ERROR(e) (errno=(e))
#endif

#if RP_LEVEL
typedef struct { unsigned depth, phase, sampled, tick_depth; uint64_t clock; } RpCheckpoint;
typedef struct { unsigned kind, entered, tick_entered; } RpCall;
/* Storage never allocates, changes GC thresholds, or retains a Ru root. */
typedef struct { uint64_t calls, sampled_calls, sampled_ns; } RpStage;
typedef struct { uint64_t calls, heap_entries, roots; } RpCallback;
typedef struct {
    unsigned active, started, complete, valid, phase, depth, sampled, tick_depth;
    unsigned phase_stack[RP_DEPTH];
    uint64_t generation, batches, sample_batches, clock_calls, last_clock;
    uint64_t alloc_requests, alloc_successes, alloc_requested_bytes;
    uint64_t realloc_requests, realloc_successes, realloc_requested_bytes;
    uint64_t env_creates, binding_creates, env_comparisons;
    uint64_t token_calls, empty_fastpath_hits, fold_rows;
    uint64_t gc_collections, gc_heap_scans, gc_marked, gc_freed, gc_work;
    uint64_t peak_live, decoded_events, snapshot_words, feed_bytes, style_bytes;
    uint64_t raw_style_hash, raw_style_bytes, raw_style_calls;
    uint64_t trace, trace_batches, last_bytes, last_line, last_done;
    uint64_t callback_max_depth, restores;
    const void *target;
    const char *failure;
    RpStage stages[RP_PHASES];
    RpCallback callbacks[3][RP_CALLBACK_DEPTH+1][2][RP_PHASES];
} RpState;
static RpState rp = {.valid=1, .trace=UINT64_C(14695981039346656037)};
static uint64_t rp_frequency;
static uint64_t rp_total_clock_calls;
static struct {
    unsigned done, valid;
    uint64_t pairs, clock_calls, min_ns, median_ns, p95_ns, max_ns;
} rp_calibration;
static void rp_invalid(const char *why) { rp.valid=0; if (!rp.failure) rp.failure=why; }
static void rp_add(uint64_t *value, uint64_t amount) {
    if (!rp.active || !rp.valid) return;
    if (*value > UINT64_MAX-amount) { rp_invalid("counter_overflow"); return; }
    *value += amount;
}
#define RP_COUNT(field,n) rp_add(&rp.field,(uint64_t)(n))
/* Clock accounting includes attempts outside the active counter interval. */
static void rp_clock_count(uint64_t *value) {
    if (*value==UINT64_MAX) rp_invalid("counter_overflow"); else ++*value;
}
static uint64_t rp_clock(void) {
    RpError saved=RP_SAVE_ERROR(); uint64_t value=0;
    rp_clock_count(&rp_total_clock_calls);
    if (rp.active) rp_clock_count(&rp.clock_calls);
#if defined(_WIN32)
    LARGE_INTEGER now, frequency;
    if (!rp_frequency) {
        if (QueryPerformanceFrequency(&frequency) && frequency.QuadPart>0)
            rp_frequency=(uint64_t)frequency.QuadPart;
    }
    if (rp_frequency && QueryPerformanceCounter(&now) && now.QuadPart>=0) {
        uint64_t q=(uint64_t)now.QuadPart;
        uint64_t seconds=q/rp_frequency, remainder=q%rp_frequency, fractional;
        if (seconds>UINT64_MAX/UINT64_C(1000000000) ||
            remainder>UINT64_MAX/UINT64_C(1000000000)) rp_invalid("clock_overflow");
        else {
            fractional=remainder*UINT64_C(1000000000)/rp_frequency;
            value=seconds*UINT64_C(1000000000);
            if (value>UINT64_MAX-fractional) { rp_invalid("clock_overflow"); value=0; }
            else value+=fractional;
        }
    } else rp_invalid("clock_failure");
#else
    struct timespec now;
    rp_frequency=UINT64_C(1000000000);
    if (clock_gettime(CLOCK_MONOTONIC,&now)==0 && now.tv_sec>=0 && now.tv_nsec>=0 && now.tv_nsec<1000000000L) {
        if ((uint64_t)now.tv_sec>(UINT64_MAX-(uint64_t)now.tv_nsec)/UINT64_C(1000000000))
            rp_invalid("clock_overflow");
        else value=(uint64_t)now.tv_sec*UINT64_C(1000000000)+(uint64_t)now.tv_nsec;
    } else rp_invalid("clock_failure");
#endif
    RP_RESTORE_ERROR(saved); return value;
}
static void rp_calibrate(void) {
    uint64_t samples[RP_CALIBRATION_PAIRS], a, b, value;
    unsigned i,j;
    if (RP_LEVEL!=2 || rp_calibration.done) return;
    if (rp.active) { rp_invalid("calibration_in_active_interval"); return; }
    rp_calibration.done=1;
    for(i=0;i<RP_CALIBRATION_PAIRS;++i) {
        a=rp_clock(); b=rp_clock();
        rp_calibration.clock_calls+=2; ++rp_calibration.pairs;
        if(b<a) rp_invalid("clock_reversed");
        samples[i]=b>=a ? b-a : 0;
    }
    /* Fixed-size insertion sort, outside the measured interval; no allocation. */
    for(i=1;i<RP_CALIBRATION_PAIRS;++i) {
        value=samples[i]; j=i;
        while(j && samples[j-1]>value) { samples[j]=samples[j-1]; --j; }
        samples[j]=value;
    }
    rp_calibration.min_ns=samples[0];
    rp_calibration.median_ns=samples[63]+(samples[64]-samples[63])/2;
    rp_calibration.p95_ns=samples[121]; /* nearest rank ceil(.95*128). */
    rp_calibration.max_ns=samples[127];
    rp_calibration.valid=rp.valid;
}
static void rp_charge(uint64_t now) {
    if (rp.active && rp.valid && rp.sampled && rp.phase && rp.last_clock) {
        if (now<rp.last_clock) rp_invalid("clock_reversed");
        else rp_add(&rp.stages[rp.phase].sampled_ns,now-rp.last_clock);
    }
    rp.last_clock=now;
}
static RpCheckpoint rp_checkpoint(void) {
    RpCheckpoint c={rp.depth,rp.phase,rp.sampled,rp.tick_depth,rp.last_clock}; return c;
}
static void rp_restore(RpCheckpoint c) {
    /* Called for normal return, panic, both native longjmp sites and trap OOM.
     * c lives in the trap, or is an unchanged pre-setjmp automatic value. */
    uint64_t now=0;
    if (c.depth>RP_DEPTH || c.phase>=RP_PHASES || c.sampled>1) { rp_invalid("bad_checkpoint"); return; }
    if (rp.depth==c.depth && rp.phase==c.phase && rp.sampled==c.sampled) {
        rp.tick_depth=c.tick_depth; RP_COUNT(restores,1); return;
    }
    if (rp.active && rp.valid && (rp.sampled || c.sampled)) {
        now=rp_clock(); rp_charge(now);
    }
    rp.depth=c.depth; rp.phase=c.phase; rp.sampled=c.sampled; rp.tick_depth=c.tick_depth;
    rp.last_clock=rp.active && rp.sampled && rp.valid ? now : 0;
    RP_COUNT(restores,1);
}
static unsigned rp_enter(unsigned phase) {
    uint64_t now=0;
    if (!rp.active || !rp.valid || !phase || phase>=RP_PHASES) return 0;
    if (rp.depth>=RP_DEPTH) { rp_invalid("phase_depth_overflow"); return 0; }
    if (rp.sampled) { now=rp_clock(); rp_charge(now); }
    rp.phase_stack[rp.depth++]=rp.phase; rp.phase=phase;
    rp_add(&rp.stages[phase].calls,1);
    if (rp.sampled) rp_add(&rp.stages[phase].sampled_calls,1);
    rp.last_clock=now; return 1;
}
static void rp_leave(unsigned entered) {
    if (!entered) return;
    if (!rp.depth) { rp_invalid("phase_depth_underflow"); return; }
    if (rp.active && rp.valid && rp.sampled) rp_charge(rp_clock());
    rp.phase=rp.phase_stack[--rp.depth];
}
static RpCall rp_call_enter(unsigned kind) {
    RpCall c={kind,0,0};
    if (kind==10) {
        if(rp.tick_depth==UINT_MAX) rp_invalid("tick_depth_overflow");
        else { ++rp.tick_depth; c.tick_entered=1; }
    }
    if (kind>=1 && kind<=4) c.entered=rp_enter(kind);
    if (kind==6) RP_COUNT(token_calls,1);
    return c;
}
static void rp_call_leave(RpCall c) {
    rp_leave(c.entered);
    if (c.tick_entered) { if (rp.tick_depth) --rp.tick_depth; else rp_invalid("tick_depth_underflow"); }
}
static void rp_begin(const void *target,uint64_t generation) {
    unsigned tick=rp.tick_depth, valid=rp.valid;
    const char *failure=rp.failure;
    if (rp.started) return;
    memset(&rp,0,sizeof(rp)); rp.valid=valid; rp.failure=failure; rp.started=1;
    rp.tick_depth=tick; rp.target=target; rp.generation=generation;
    rp.trace=UINT64_C(14695981039346656037);
    rp.raw_style_hash=UINT64_C(14695981039346656037);
    rp_calibrate();
    if (rp_calibration.done && !rp_calibration.valid && rp.valid) rp_invalid("calibration_invalid");
    rp.active=1;
}
static void rp_batch(void) {
    if (!rp.active || !rp.valid) return;
    if (rp.depth || rp.phase) { rp_invalid("unbalanced_batch_entry"); return; }
    RP_COUNT(batches,1);
    rp.sampled=RP_LEVEL==2 && rp.batches%64==0;
    if (rp.sampled) RP_COUNT(sample_batches,1);
    rp.last_clock=0;
}
static void rp_batch_end(void) {
    if (!rp.active) return;
    if (rp.depth || rp.phase) rp_invalid("unbalanced_batch_end");
    rp.sampled=0; rp.last_clock=0;
}
static void rp_finish(int success) {
    if (!rp.active) return;
    if (rp.depth || rp.phase) rp_invalid("unbalanced_interval_end");
    rp.complete=success && rp.valid;
    rp.sampled=0; rp.active=0;
}
static void rp_hash_u32(uint32_t value) {
    unsigned i;
    if (!rp.active || !rp.valid) return;
    for(i=0;i<4;++i) { rp.trace^=(value>>(8*i))&255u; rp.trace*=UINT64_C(1099511628211); }
}
static void rp_style_trace(const unsigned char *bytes,size_t count) {
    size_t i;
    if (!rp.active || !rp.valid) return;
#if RP_NATIVE_STYLE_TRACE
    if(count && !bytes) { rp_invalid("raw_style_null"); return; }
    RP_COUNT(raw_style_bytes,count); RP_COUNT(raw_style_calls,1);
    if (!rp.valid) return;
    /* Intentional modulo-2^64 arithmetic belongs to FNV, not a counter. */
    for(i=0;i<count;++i) { rp.raw_style_hash^=bytes[i]; rp.raw_style_hash*=UINT64_C(1099511628211); }
#else
    (void)i; (void)bytes; (void)count; rp_invalid("raw_style_unsupported");
#endif
}
static void rp_alloc_request(size_t bytes) { RP_COUNT(alloc_requests,1); RP_COUNT(alloc_requested_bytes,bytes); }
static void rp_alloc_success(void) { RP_COUNT(alloc_successes,1); }
static void rp_realloc_request(size_t bytes) { RP_COUNT(realloc_requests,1); RP_COUNT(realloc_requested_bytes,bytes); }
static void rp_realloc_success(void) { RP_COUNT(realloc_successes,1); }
static void rp_callback(unsigned kind,unsigned depth,uint64_t heap_entries,uint64_t roots) {
    RpCallback *c; unsigned bucket=kind==8?0:kind==9?1:2;
    if (!rp.active || !rp.valid) return;
    if (depth>rp.callback_max_depth) rp.callback_max_depth=depth;
    if (depth>RP_CALLBACK_DEPTH) { rp_invalid("callback_depth_overflow"); return; }
    if (rp.phase>=RP_PHASES) { rp_invalid("bad_callback_phase"); return; }
    c=&rp.callbacks[bucket][depth][rp.tick_depth?1:0][rp.phase];
    rp_add(&c->calls,1); rp_add(&c->heap_entries,heap_entries); rp_add(&c->roots,roots);
}
static void rp_emit(void) {
    RpError saved=RP_SAVE_ERROR(); unsigned i,j,k,p; int comma=0;
    static const char *names[]={"residual","scan_result","decoder","policy","publish"};
    static const char *callbacks[]={"main_window","child_subclass","other"};
    printf("RU_SYNTAX_PROFILE {\"schema\":1,\"path\":\"%s\",\"mode\":\"%s\",\"instrumentation\":\"%s\",\"counter_interval\":\"first_batch_to_last_batch\",\"valid\":%s,\"started\":%s,\"complete\":%s,\"failure\":",RP_PATH,RP_MODE,RP_LEVEL==1?"counts":"sampled",rp.valid?"true":"false",rp.started?"true":"false",rp.complete?"true":"false");
    if(rp.failure) printf("\"%s\"",rp.failure); else printf("null");
    printf(",\"generation\":%" PRIu64 ",\"corpus\":{\"sha256\":\"%s\",\"bytes\":1000000,\"scalars\":636370},\"sampling\":{\"origin\":\"one_based_batch_divisible_by_64\",\"stride\":64,\"sample_batches\":%" PRIu64 ",\"clock_calls\":%" PRIu64 ",\"total_clock_calls\":%" PRIu64 ",\"frequency_hz\":%" PRIu64 ",\"calibration\":",rp.generation,RP_CORPUS_SHA,rp.sample_batches,rp.clock_calls,rp_total_clock_calls,rp_frequency);
    if (RP_LEVEL==2 && rp_calibration.done) {
        printf("{\"pairs\":%" PRIu64 ",\"clock_calls\":%" PRIu64 ",\"valid\":%s,\"min_ns\":",rp_calibration.pairs,rp_calibration.clock_calls,rp_calibration.valid?"true":"false");
        if (rp_calibration.valid) printf("%" PRIu64 ",\"median_ns\":%" PRIu64 ",\"p95_ns\":%" PRIu64 ",\"max_ns\":%" PRIu64,rp_calibration.min_ns,rp_calibration.median_ns,rp_calibration.p95_ns,rp_calibration.max_ns);
        else printf("null,\"median_ns\":null,\"p95_ns\":null,\"max_ns\":null");
        printf("}");
    } else printf("null");
    printf("},\"stages\":{");
    for(i=1;i<RP_PHASES;++i) printf("%s\"%s\":{\"calls\":%" PRIu64 ",\"sampled_calls\":%" PRIu64 ",\"sampled_ns\":%" PRIu64 "}",i==1?"":",",names[i],rp.stages[i].calls,rp.stages[i].sampled_calls,rp.stages[i].sampled_ns);
    printf("},\"counters\":{");
#define RP_PRINT(field) do { printf("%s\"" #field "\":%" PRIu64,comma?",":"",rp.field); comma=1; } while(0)
    RP_PRINT(batches); RP_PRINT(alloc_requests); RP_PRINT(alloc_successes); RP_PRINT(alloc_requested_bytes);
    RP_PRINT(realloc_requests); RP_PRINT(realloc_successes); RP_PRINT(realloc_requested_bytes);
    RP_PRINT(env_creates); RP_PRINT(binding_creates); RP_PRINT(env_comparisons); RP_PRINT(token_calls);
    RP_PRINT(empty_fastpath_hits); RP_PRINT(fold_rows); RP_PRINT(gc_collections); RP_PRINT(gc_heap_scans);
    RP_PRINT(gc_marked); RP_PRINT(gc_freed); RP_PRINT(gc_work); RP_PRINT(peak_live); RP_PRINT(decoded_events);
    RP_PRINT(snapshot_words); RP_PRINT(feed_bytes); RP_PRINT(style_bytes);
    RP_PRINT(callback_max_depth); RP_PRINT(restores);
#undef RP_PRINT
    printf(",\"suffix_copy_bytes\":null,\"suffix_validate_bytes\":null},\"trace\":{\"algorithm\":\"fnv1a64_le_u32_v1\",\"value\":\"%016" PRIx64 "\",\"batches\":%" PRIu64 ",\"last_bytes\":%" PRIu64 ",\"last_line\":%" PRIu64 ",\"last_done\":%" PRIu64 "},\"raw_style_trace\":",rp.trace,rp.trace_batches,rp.last_bytes,rp.last_line,rp.last_done);
#if RP_NATIVE_STYLE_TRACE
    printf("{\"algorithm\":\"fnv1a64_bytes_v1\",\"value\":\"%016" PRIx64 "\",\"bytes\":%" PRIu64 ",\"calls\":%" PRIu64 "}",rp.raw_style_hash,rp.raw_style_bytes,rp.raw_style_calls);
#else
    printf("null");
#endif
    printf(",\"callbacks\":[");
    comma=0;
    for(i=0;i<3;++i) for(j=0;j<=RP_CALLBACK_DEPTH;++j) for(k=0;k<2;++k) for(p=0;p<RP_PHASES;++p) {
        RpCallback *c=&rp.callbacks[i][j][k][p]; if(!c->calls) continue;
        printf("%s{\"kind\":\"%s\",\"depth\":%u,\"in_tick\":%s,\"phase\":\"%s\",\"calls\":%" PRIu64 ",\"heap_entries\":%" PRIu64 ",\"roots\":%" PRIu64 "}",comma?",":"",callbacks[i],j,k?"true":"false",names[p],c->calls,c->heap_entries,c->roots); comma=1;
    }
    printf("]}\n"); fflush(stdout); RP_RESTORE_ERROR(saved);
}
#else
static void rp_emit(void) {
    RpError saved=RP_SAVE_ERROR();
    printf("RU_SYNTAX_PROFILE {\"schema\":1,\"path\":\"%s\",\"mode\":\"%s\",\"instrumentation\":\"off\",\"counter_interval\":null,\"valid\":true,\"started\":null,\"complete\":null,\"failure\":null,\"generation\":null,\"corpus\":{\"sha256\":\"%s\",\"bytes\":1000000,\"scalars\":636370},\"sampling\":null,\"stages\":null,\"counters\":null,\"trace\":null,\"raw_style_trace\":null,\"callbacks\":null}\n",RP_PATH,RP_MODE,RP_CORPUS_SHA);
    fflush(stdout); RP_RESTORE_ERROR(saved);
}
#endif
#endif
