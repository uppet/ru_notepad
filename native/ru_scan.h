#ifndef RU_NOTEPAD_SCAN_H
#define RU_NOTEPAD_SCAN_H
#include <stdint.h>
#include <stddef.h>
#ifdef _WIN32
#define RU_SCAN_API __declspec(dllexport)
#else
#define RU_SCAN_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
#define RU_SCAN_ABI 0x00010000u
#define RU_SCAN_MAX_INPUT 65536u
#define RU_SCAN_MAX_STYLES (RU_SCAN_MAX_INPUT+16u)
#define RU_SCAN_EVENT_CAPACITY 64u
#define RU_SCAN_CONFIG_LIMIT 128u
/* Status 0 OK, 1 OUTPUT_FULL (resume remaining input), 2 BAD_ARGUMENT,
 * 3 INVALID_UTF8, 4 BAD_STATE. Success always consumes input, emits events,
 * finishes EOF, or retains <=16 bytes awaiting the next input. An empty
 * non-EOF feed may wait without progress. OUTPUT_FULL always consumes/styles
 * bytes or emits an event; resume even if EOF was already true. Errors leave
 * state unchanged and zero the result except status; ignore output buffers. */
enum { RU_SCAN_OK=0, RU_SCAN_OUTPUT_FULL=1, RU_SCAN_BAD_ARGUMENT=2,
       RU_SCAN_INVALID_UTF8=3, RU_SCAN_BAD_STATE=4 };
enum { RU_EVENT_NAME=1, RU_EVENT_NUMBER=2, RU_EVENT_STRING=3,
       RU_EVENT_OPERATOR=4, RU_EVENT_BLOCK_OPEN=5,
       RU_EVENT_BLOCK_CLOSE=6, RU_EVENT_EOL=7 };
/* head: kind[0:8], Ru-supplied grammar tag[8:16], style[16:24],
 * absolute UTF8 start byte[24:56]. tail: length[0:32], start line[32:64]. */
typedef struct RuScanEvent { uint64_t head, tail; } RuScanEvent;
/* Windows x64 / ordinary C layout: six u32 then two u64, total 40 bytes. */
typedef struct RuScanResult {
    uint32_t status, consumed, styled, events, line, done;
    uint64_t start, bytes;
} RuScanResult;
/* No function retains a caller pointer. Config remains caller-owned/immutable;
 * pass it on every feed. State owns all carry/prefix bytes, never input text.
 * All memory must be naturally aligned and independently owned by the caller. */
RU_SCAN_API uint32_t ru_scan_abi(void);
RU_SCAN_API uint32_t ru_scan_config_size(void);
RU_SCAN_API uint32_t ru_scan_state_size(void);
/* Configuration UTF8 lines: decimalTag:decimalStyle:exactWord\n.
 * At most 128 distinct words, 1..16 Unicode scalars / 1..64 bytes each. Tags/styles are 0..255.
 * Init validates and COPIES all words into memory; it never retains words.
 * Ru owns this table; no keyword, type or folding vocabulary lives in C. */
RU_SCAN_API uint32_t ru_scan_config_init(void *memory,uint32_t size,
                                        const char *words,uint32_t length);
RU_SCAN_API uint32_t ru_scan_state_init(void *memory,uint32_t size);
RU_SCAN_API uint32_t ru_scan_state_copy(void *target,const void *source,uint32_t size);
/* State is entirely initialized, padding-free and canonicalized on feed.
 * copy/equal require buffers of state_size bytes. equal returns only 0/1;
 * invalid magic compares unequal. Position limits are checked before commit
 * (32,000,000 bytes maximum) so no 32-bit event field can silently wrap. */
RU_SCAN_API uint32_t ru_scan_state_equal(const void *left,const void *right);
/* Input may split UTF8 scalars. Invalid/overlong/surrogate/NUL sequences are
 * rejected; EOF rejects an incomplete scalar. Styles cover [result.start,
 * result.start+styled), with result.bytes == result.start+styled, which can include the previous <=16-byte carry.
 * input_offset selects a remaining slice of a caller-owned window without
 * pointer arithmetic in Ru. consumed counts bytes accepted after that offset.
 * consumed is INPUT bytes accepted, not styled bytes. Maintain a separate
 * feed cursor. OUTPUT_FULL never drops tokens; resume the unaccepted input.
 * Apply style bytes before Ru's small NAME classification corrections.
 * capacities: styles >= input length+16; events >=8 and <=64. */
RU_SCAN_API uint32_t ru_scan_feed(const void *config,void *state,
    const uint8_t *input,uint32_t length,uint32_t input_offset,uint32_t eof,
    uint8_t *styles,uint32_t styles_capacity,
    RuScanEvent *events,uint32_t events_capacity,RuScanResult *result);
#ifdef __cplusplus
}
#endif
#endif
