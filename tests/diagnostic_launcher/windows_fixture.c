/* Cross-build fixture. Execute only on native Windows, explicitly opted in. */
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
#ifndef FIXTURE_MODE
#define FIXTURE_MODE 0
#endif
#define main ru_program_main
int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    fputs("fixture stdout marker\n", stdout);
    fputs("fixture stderr marker\n", stderr);
#if FIXTURE_MODE == 1
    return 7; /* Nonzero can be module-init panic: launcher dialog required. */
#elif FIXTURE_MODE == 2
    exit(23); /* Orderly fatal runtime exit: atexit must show a log path. */
#elif FIXTURE_MODE == 3
    HWND window = CreateWindowExW(0, L"STATIC", L"Synthetic diagnostic fixture",
                                  WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
                                  400, 200, NULL, NULL, GetModuleHandleW(NULL), NULL);
    if (!window) return 9;
    ShowWindow(window, SW_SHOW);
    fputs("fixture window exists before fatal exit\n", stderr);
    exit(23); /* Fatal popup must disable this existing current-thread window. */
#else
    return 0;
#endif
}
#undef main
#include "../../packaging/diagnostic_launcher.c"
