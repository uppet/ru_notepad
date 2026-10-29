/* Fixed C-only adapter. Never rename or rewrite the stage3 LLVM main symbol. */
extern int main(int argc, char **argv);
static int ru_bootstrap_main_bridge(int argc, char **argv)
{
    /* Defined BEFORE macros: this calls the native LLVM object's real main. */
    return main(argc, argv);
}

#define main ru_bootstrap_diagnostic_main
#define ru_program_main ru_bootstrap_main_bridge
#include "diagnostic_launcher.c"
#undef ru_program_main
#undef main

#ifndef RU_BOOTSTRAP_BRIDGE_TEST
#include <windows.h>
#include <shellapi.h>
#include <stdlib.h>
#include <stdint.h>

/* CRT startup initializes C runtime before entering this wrapper. All argv
 * allocations are owned here, remain live through the diagnostic/Ru call, and
 * are freed on every returning path. exit() is handled by CRT/OS teardown. */
int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR command, int show)
{
    int argc = 0, index, status = EXIT_FAILURE;
    wchar_t **wide = NULL;
    char **utf8 = NULL;
    (void)instance; (void)previous; (void)command; (void)show;
    wide = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!wide || argc <= 0 || (size_t)argc >= SIZE_MAX / sizeof(*utf8)) goto failed;
    utf8 = (char **)calloc((size_t)argc + 1u, sizeof(*utf8));
    if (!utf8) goto failed;
    for (index = 0; index < argc; ++index) {
        int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide[index], -1,
                                       NULL, 0, NULL, NULL);
        if (size <= 0) goto failed;
        utf8[index] = (char *)malloc((size_t)size);
        if (!utf8[index] || WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
                wide[index], -1, utf8[index], size, NULL, NULL) != size) goto failed;
    }
    status = ru_bootstrap_diagnostic_main(argc, utf8);
    goto cleanup;
failed:
    MessageBoxW(NULL, L"Ru Notepad could not decode or allocate its command line. Startup stopped.",
                L"Ru Notepad startup error", MB_OK | MB_ICONERROR);
cleanup:
    if (utf8) {
        for (index = 0; index < argc; ++index) free(utf8[index]);
        free(utf8);
    }
    if (wide) LocalFree(wide);
    return status;
}
#endif
