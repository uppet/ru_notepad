#ifndef RU_DIRECTORY_IO_H
#define RU_DIRECTORY_IO_H
#include <stdint.h>
#ifdef _WIN32
#define RU_DIR_API __declspec(dllexport)
#else
#define RU_DIR_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
#define RU_DIR_ABI 0x00010000u
#define RU_DIR_EVENT_BYTES 8192u
#define RU_DIR_PATH_UNITS 1024u
#define RU_DIR_DATA_BYTES 4096u
#define RU_DIR_QUEUE_SLOTS 4u
#define RU_DIR_FILE_LIMIT 10000u
#define RU_DIR_DIRECTORY_LIMIT 2000u
#define RU_DIR_DEPTH_LIMIT 32u
#define RU_DIR_FILE_BYTES 8388608ull
#define RU_DIR_READ_BYTES 268435456ull
enum { RU_DIR_OK=0, RU_DIR_EMPTY=1, RU_DIR_BUSY=2, RU_DIR_BAD_ARGUMENT=3,
       RU_DIR_UNSUPPORTED=4, RU_DIR_SYSTEM_ERROR=5, RU_DIR_STOPPING=6, RU_DIR_CANCELLED=7 };
enum { RU_DIR_START=1,RU_DIR_DATA=2,RU_DIR_END=3,RU_DIR_SKIP=4,
       RU_DIR_ERROR=5,RU_DIR_JOB_END=6 };
enum { RU_DIR_REASON_NONE=0,RU_DIR_REASON_PATH=1,RU_DIR_REASON_UNSAFE=2,
       RU_DIR_REASON_IO=3,RU_DIR_REASON_CHANGED=4,RU_DIR_REASON_SIZE=5,
       RU_DIR_REASON_FILES=6,RU_DIR_REASON_DIRECTORIES=7,RU_DIR_REASON_DEPTH=8,
       RU_DIR_REASON_READ_BUDGET=9,RU_DIR_REASON_CANCELLED=10,
       RU_DIR_REASON_ENUMERATION=11,RU_DIR_REASON_PLATFORM=12 };
enum { RU_DIR_IDLE=0,RU_DIR_ACTIVE=1,RU_DIR_DRAINING=2,RU_DIR_FINISHED=3 };
/* ABI layout: u32 fields offsets 0..60; u64 fields offsets 64..104;
 * path offset112, data2160, padding6256; total8192. All unused bytes zero.
 * pathUnits excludes terminator; paths UTF16, data opaque bytes. Sequence
 * starts at 1, contiguous across all events. fileSequence increases for each
 * charged nondirectory entry. START/DATA/END/SKIP retain that fileSequence.
 * END flags=1 only after exact-size read plus verified EOF and final metadata.
 * ERROR flag bit1 (2) denotes fatal. SKIP/ERROR bit2 (4) denotes a
 * directory/root exclusion with fileSequence=0, never a file abort. File
 * SKIP/ERROR retains the current fileSequence. Other flags are zero.
 * Metadata checks are not a snapshot guarantee against writable mappings.
 * JOB_END status is a reason (0 complete); counters include skipped entries.
 * DATA offset is absolute raw byte offset. readBytes includes EOF probes.
 * No result matching, decoding, UI access, callbacks or retained caller data.
 */
typedef struct RuDirEvent {
    uint32_t abi,size,kind,reason,generation,sequence,fileSequence,flags;
    uint32_t pathUnits,dataBytes,files,dirs,skipped,errors,status,reserved;
    uint64_t offset,rawSize,volume,fileId,stamp,readBytes;
    uint16_t path[RU_DIR_PATH_UNITS];
    uint8_t data[RU_DIR_DATA_BYTES];
    uint8_t padding[1936];
} RuDirEvent;
RU_DIR_API uint32_t ru_dir_abi(void);
RU_DIR_API uint32_t ru_dir_event_size(void);
/* Public calls must be serialized on the owning UI thread. They are
 * nonblocking, bounded, never enumerate/read paths or join.
 * start accepts only strictly increasing nonzero generations and strict absolute X:\\ paths, copied before return.
 * Root and assembled paths are capped at 1023 UTF16 units.
 * One worker active or retiring. BUSY means retry later; STOPPING means retiring.
 * poll writes exactly event_size bytes on OK, nothing on EMPTY/BUSY/error.
 * release discards queued events and requests cancellation, never waits.
 * cancel retains queued events; worker may drop terminal event on cancellation
 * to avoid blocking a full queue. status exposes FINISHED even without it.
 * To reclaim: release, then status until IDLE (or start until not BUSY).
 * CancelSynchronousIo is best effort: stalled device I/O keeps slot DRAINING.
 * No replacement worker can start until OS thread termination is observed.
 */
RU_DIR_API uint32_t ru_dir_start(uint32_t abi,uint32_t generation,
                                const uint16_t *root,uint32_t rootUnits);
RU_DIR_API uint32_t ru_dir_poll(uint32_t abi,uint32_t generation,
                               RuDirEvent *event,uint32_t eventBytes);
RU_DIR_API uint32_t ru_dir_cancel(uint32_t abi,uint32_t generation);
RU_DIR_API uint32_t ru_dir_release(uint32_t abi,uint32_t generation);
/* Returns lifecycle value, or UINT32_MAX for ABI mismatch / transient lock. */
RU_DIR_API uint32_t ru_dir_status(uint32_t abi);
/* App-shutdown only: permanently disables starts, discards events, requests
 * cancellation. Drops the observation handle without terminating the worker. No more
 * polling or retry is required: valid generation returns OK even under queue
 * lock contention. Caller may unload its DLL reference immediately. */
RU_DIR_API uint32_t ru_dir_abandon(uint32_t abi,uint32_t generation);
/* Modal UI picker, separate from nonblocking transport. owner is HWND as u64;
 * caller owns >=1024 UTF16 units. CANCELLED leaves output empty. COM/PIDL are
 * locally balanced; extraction fails closed rather than truncating. */
RU_DIR_API uint32_t ru_dir_pick_folder(uint64_t owner,uint16_t *out,uint32_t capacity);
#ifdef __cplusplus
}
#endif
#endif
