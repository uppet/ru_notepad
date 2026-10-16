/*
 * GUI diagnostic entry point. Include AFTER the generated C, whose main must
 * have been renamed to ru_program_main. This owns no editor/document behavior.
 *
 * Logs use CREATE_NEW, never reopen a log by name, and are never uploaded or
 * opened automatically. The launcher records lifecycle events, not argv or
 * document contents. Ru runtime stdout/stderr is captured without filtering;
 * treat a diagnostic log as potentially private before sharing it.
 *
 * atexit covers orderly exit() before Ru main returns. It cannot handle every
 * crash, abort(), TerminateProcess(), or power loss and is not crash recovery.
 */
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define RU_DIAG_PATH_CAP 1024u
#define RU_DIAG_NAME_CAP 96u
#define RU_DIAG_ATTEMPTS 64u

/* Pure bounded path policy, also compiled and executed by host-side tests. */
static int ru_diag_local_path(const wchar_t *path)
{
    size_t i, component = 3u;
    if (!path || !((path[0] >= L'A' && path[0] <= L'Z') ||
                   (path[0] >= L'a' && path[0] <= L'z')) ||
        path[1] != L':' || path[2] != L'\\') return 0;
    for (i = 3u; path[i]; ++i) {
        wchar_t c = path[i];
        if (c < 32 || c == L'/' || c == L':' || c == L'"' ||
            c == L'<' || c == L'>' || c == L'|' || c == L'?' || c == L'*')
            return 0;
        if (c == L'\\') {
            if (i == component || path[i - 1u] == L'.' || path[i - 1u] == L' ')
                return 0;
            component = i + 1u;
        }
    }
    return i == component || (path[i - 1u] != L'.' && path[i - 1u] != L' ');
}

static int ru_diag_join(wchar_t *out, size_t cap,
                        const wchar_t *directory, const wchar_t *name)
{
    size_t d, n, slash;
    if (!out || !cap || !directory || !name) return 0;
    out[0] = L'\0';
    d = wcslen(directory);
    n = wcslen(name);
    if (!d || !n) return 0;
    slash = directory[d - 1u] == L'\\' ? 0u : 1u;
    if (d >= cap || slash >= cap - d || n >= cap - d - slash) return 0;
    wmemcpy(out, directory, d);
    if (slash) out[d++] = L'\\';
    wmemcpy(out + d, name, n + 1u);
    return 1;
}

static int ru_diag_log_path(wchar_t *out, size_t cap, const wchar_t *directory,
                            unsigned long pid, unsigned long high,
                            unsigned long low, unsigned attempt)
{
    wchar_t name[RU_DIAG_NAME_CAP];
    int count;
    if (!out || !cap) return 0;
    out[0] = L'\0';
    if (attempt >= RU_DIAG_ATTEMPTS || !ru_diag_local_path(directory)) return 0;
    count = swprintf(name, RU_DIAG_NAME_CAP,
                     L"ru_notepad-%08lx-%08lx%08lx-%02u.log",
                     pid, high, low, attempt);
    if (count < 0 || (size_t)count >= RU_DIAG_NAME_CAP) return 0;
    return ru_diag_join(out, cap, directory, name);
}

static int ru_diag_should_show_failure(int started, int returned, int status)
{
    return started && (!returned || status != 0);
}

#if defined(_WIN32)
#include <windows.h>
#include <shlobj.h>
#include <fcntl.h>
#include <io.h>
#include <stdint.h>

static wchar_t ru_diag_path[RU_DIAG_PATH_CAP];
static int ru_diag_running;
static int ru_diag_returned;
static int ru_diag_return_status;
static int ru_diag_redirected;

/* Never follow UNC paths, mapped network drives, or known reparse directories.
 * CREATE_NEW remains the no-overwrite guarantee even during namespace races.
 * Known-folder lookup avoids using untrusted TMP/TEMP environment strings.
 */
static int ru_diag_local_directory(const wchar_t *directory)
{
    wchar_t prefix[RU_DIAG_PATH_CAP], root[4];
    size_t i, length;
    UINT kind;
    if (!ru_diag_local_path(directory)) return 0;
    length = wcslen(directory);
    if (length >= RU_DIAG_PATH_CAP) return 0;
    wmemcpy(root, directory, 3u);
    root[3] = L'\0';
    kind = GetDriveTypeW(root);
    if (kind != DRIVE_FIXED && kind != DRIVE_REMOVABLE && kind != DRIVE_RAMDISK)
        return 0;
    wmemcpy(prefix, directory, length + 1u);
    for (i = 3u; i <= length; ++i) {
        if (i == length || prefix[i] == L'\\') {
            wchar_t saved = prefix[i];
            DWORD attributes;
            prefix[i] = L'\0';
            attributes = GetFileAttributesW(prefix);
            prefix[i] = saved;
            if (attributes == INVALID_FILE_ATTRIBUTES ||
                !(attributes & FILE_ATTRIBUTE_DIRECTORY) ||
                (attributes & FILE_ATTRIBUTE_REPARSE_POINT)) return 0;
        }
    }
    return 1;
}

static HANDLE ru_diag_create_in(const wchar_t *directory)
{
    FILETIME time;
    unsigned attempt;
    DWORD pid = GetCurrentProcessId();
    if (!ru_diag_local_directory(directory)) return INVALID_HANDLE_VALUE;
    GetSystemTimeAsFileTime(&time);
    for (attempt = 0u; attempt < RU_DIAG_ATTEMPTS; ++attempt) {
        HANDLE file;
        BY_HANDLE_FILE_INFORMATION info;
        if (!ru_diag_log_path(ru_diag_path, RU_DIAG_PATH_CAP, directory,
                              pid, time.dwHighDateTime, time.dwLowDateTime,
                              attempt)) break;
        file = CreateFileW(ru_diag_path, GENERIC_WRITE, FILE_SHARE_READ, NULL,
                           CREATE_NEW,
                           FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
                           NULL);
        if (file != INVALID_HANDLE_VALUE) {
            if (GetFileType(file) == FILE_TYPE_DISK &&
                GetFileInformationByHandle(file, &info) &&
                !(info.dwFileAttributes &
                  (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)))
                return file;
            CloseHandle(file);
            break;
        }
        if (GetLastError() != ERROR_FILE_EXISTS &&
            GetLastError() != ERROR_ALREADY_EXISTS) break;
    }
    ru_diag_path[0] = L'\0';
    return INVALID_HANDLE_VALUE;
}

static HANDLE ru_diag_create_log(void)
{
    wchar_t directory[RU_DIAG_PATH_CAP], local[MAX_PATH];
    DWORD count = GetModuleFileNameW(NULL, directory, RU_DIAG_PATH_CAP);
    HANDLE file;
    if (count && count < RU_DIAG_PATH_CAP) {
        wchar_t *slash = wcsrchr(directory, L'\\');
        if (slash && slash >= directory + 2) {
            if (slash == directory + 2) slash[1] = L'\0';
            else *slash = L'\0';
            file = ru_diag_create_in(directory);
            if (file != INVALID_HANDLE_VALUE) return file;
        }
    }
    /* This is the current user's existing local Temp directory, never a
     * directory supplied by argv, cwd, TMP or TEMP. No folders are created.
     */
    if (SUCCEEDED(SHGetFolderPathW(NULL, CSIDL_LOCAL_APPDATA, NULL,
                                   SHGFP_TYPE_CURRENT, local)) &&
        ru_diag_join(directory, RU_DIAG_PATH_CAP, local, L"Temp")) {
        file = ru_diag_create_in(directory);
        if (file != INVALID_HANDLE_VALUE) return file;
    }
    ru_diag_path[0] = L'\0';
    return INVALID_HANDLE_VALUE;
}

/* Takes ownership of file on every path. Initialize GUI CRT streams with the
 * NUL device first: an unattached GUI process may have _fileno(stream) == -2.
 * No existing file or log path is passed to freopen.
 */
static int ru_diag_redirect(HANDLE file)
{
    int fd;
    if ((_fileno(stdin) < 0 && !_wfreopen(L"\\\\.\\NUL", L"r", stdin)) ||
        !_wfreopen(L"\\\\.\\NUL", L"w", stdout) ||
        !_wfreopen(L"\\\\.\\NUL", L"w", stderr)) {
        CloseHandle(file);
        return 0;
    }
    fd = _open_osfhandle((intptr_t)file, _O_WRONLY | _O_BINARY | _O_NOINHERIT);
    if (fd < 0) {
        CloseHandle(file); /* Ownership transfers only on successful open. */
        return 0;
    }
    if (_dup2(fd, _fileno(stdout)) != 0 ||
        _dup2(fd, _fileno(stderr)) != 0) {
        _close(fd);
        return 0;
    }
    _close(fd); /* stdout/stderr now own their duplicated handles. */
    if (setvbuf(stdout, NULL, _IONBF, 0) != 0 ||
        setvbuf(stderr, NULL, _IONBF, 0) != 0 ||
        !SetStdHandle(STD_OUTPUT_HANDLE, (HANDLE)_get_osfhandle(_fileno(stdout))) ||
        !SetStdHandle(STD_ERROR_HANDLE, (HANDLE)_get_osfhandle(_fileno(stderr))))
        return 0;
    ru_diag_redirected = 1;
    return 1;
}

static int ru_diag_flush(void)
{
    int ok = 1;
    if (!ru_diag_redirected) return 0;
    if (fflush(stdout) != 0 || ferror(stdout)) ok = 0;
    if (fflush(stderr) != 0 || ferror(stderr)) ok = 0;
    if (!FlushFileBuffers((HANDLE)_get_osfhandle(_fileno(stderr)))) ok = 0;
    return ok;
}

static void ru_diag_setup_failed(const wchar_t *reason)
{
    OutputDebugStringW(L"Ru Notepad diagnostic startup failed: ");
    OutputDebugStringW(reason);
    OutputDebugStringW(L"\n");
    MessageBoxW(NULL, reason, L"Ru Notepad startup error", MB_OK | MB_ICONERROR);
}

static void ru_diag_at_exit(void)
{
    wchar_t message[RU_DIAG_PATH_CAP + 512u];
    const wchar_t *prefix;
    int count;
    if (!ru_diag_should_show_failure(ru_diag_running, ru_diag_returned,
                                      ru_diag_return_status)) return;
    if (!ru_diag_returned)
        fputs("[launcher] Ru program exited before returning to the launcher.\n", stderr);
    prefix = ru_diag_flush()
        ? L"Ru Notepad stopped after an error or an unexpected early exit.\n\nDiagnostic log:\n"
        : L"Ru Notepad stopped after an error or an unexpected early exit.\n"
          L"The diagnostic log could not be fully written. It may be incomplete:\n";
    count = swprintf(message, sizeof(message) / sizeof(message[0]),
                     L"%ls%ls\n\nNo document recovery or emergency save was performed.\n"
                     L"If this happened during Save, the target file may already have changed.",
                     prefix, ru_diag_path);
    if (count < 0 || (size_t)count >= sizeof(message) / sizeof(message[0])) {
        ru_diag_setup_failed(L"Ru Notepad stopped unexpectedly. The diagnostic "
                             L"log location could not be displayed.");
        return;
    }
    OutputDebugStringW(message);
    MessageBoxW(NULL, message, L"Ru Notepad startup/runtime error",
                MB_OK | MB_ICONERROR | MB_TASKMODAL);
}

int main(int argc, char **argv)
{
    HANDLE log = ru_diag_create_log();
    int status;
    if (log == INVALID_HANDLE_VALUE) {
        ru_diag_setup_failed(L"Ru Notepad could not create a new diagnostic log "
                             L"beside the application or in your local Temp folder.\n"
                             L"Startup was stopped. Check the folder permissions "
                             L"and free disk space; no existing log was overwritten.");
        return EXIT_FAILURE;
    }
    if (!ru_diag_redirect(log)) {
        ru_diag_setup_failed(L"Ru Notepad could not connect its diagnostic log.\n"
                             L"Startup was stopped. The new log may be empty; "
                             L"no existing log was overwritten.");
        return EXIT_FAILURE;
    }
    if (atexit(ru_diag_at_exit) != 0) {
        fputs("[launcher] Could not register the exit diagnostic handler.\n", stderr);
        (void)ru_diag_flush();
        ru_diag_setup_failed(L"Ru Notepad could not register its diagnostic "
                             L"exit handler. Startup was stopped.");
        return EXIT_FAILURE;
    }
    fputs("Ru Notepad diagnostic log\n[launcher] Starting Ru program.\n", stderr);
    if (!ru_diag_flush()) {
        ru_diag_setup_failed(L"Ru Notepad could not write its diagnostic log.\n"
                             L"Startup was stopped. Check free disk space and "
                             L"folder permissions.");
        return EXIT_FAILURE;
    }
    ru_diag_running = 1;
    status = ru_program_main(argc, argv);
    ru_diag_return_status = status;
    ru_diag_returned = 1; /* Nonzero may be a module-init panic with no Ru dialog. */
    fprintf(stderr, "[launcher] Ru program returned with status %d.\n", status);
    if (!ru_diag_flush())
        OutputDebugStringW(L"Ru Notepad: final diagnostic log flush failed.\n");
    return status;
}
#elif !defined(RU_DIAGNOSTIC_POLICY_TEST)
#error "diagnostic_launcher.c requires Windows; host tests may compile pure path policy only"
#endif
