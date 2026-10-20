/* Test-owned memory helpers. These traversal models are deliberately NOT
 * User32 CharNextW and are not evidence of Windows ABI or dialog acceptance. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif

API void copy_memory(void *to, const void *from, uintptr_t size)
{
    memmove(to, from, size);
}

API uint32_t read_u16(const void *memory, uintptr_t size, uintptr_t index)
{
    const unsigned char *p = memory;
    if (index >= size / 2) return UINT32_MAX;
    return (uint32_t)p[index * 2] | ((uint32_t)p[index * 2 + 1] << 8);
}

API void *next_unit(const uint16_t *at)
{
    return (void *)(*at ? at + 1 : at);
}

static int combining(uint16_t unit)
{
    return (unit >= 0x0300 && unit <= 0x036f) ||
           (unit >= 0x1ab0 && unit <= 0x1aff) ||
           (unit >= 0x1dc0 && unit <= 0x1dff) ||
           (unit >= 0x20d0 && unit <= 0x20ff) ||
           (unit >= 0xfe20 && unit <= 0xfe2f);
}

API void *next_cluster(const uint16_t *at)
{
    if (!*at) return (void *)at;
    if (at[0] >= 0xd800 && at[0] <= 0xdbff &&
        at[1] >= 0xdc00 && at[1] <= 0xdfff) at += 2;
    else ++at;
    /* This also skips leading combining units after an ASCII separator. */
    while (combining(*at)) ++at;
    return (void *)at;
}

API void *next_stuck(const uint16_t *at) { return (void *)at; }
API void *next_null(const uint16_t *at) { (void)at; return NULL; }
