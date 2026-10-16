/* Native acceptance fixture only. Never shipped as the application's scanner. */
#include <stdint.h>
#ifdef _WIN32
__declspec(dllexport)
#endif
uint32_t ru_scan_abi(void) { return UINT32_C(0x00020000); }
