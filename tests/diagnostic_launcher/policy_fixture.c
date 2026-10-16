/* Native-host executable tests. No fake _WIN32 or Windows API replacements. */
#define RU_DIAGNOSTIC_POLICY_TEST 1
#include "../../packaging/diagnostic_launcher.c"
#include <assert.h>
#include <limits.h>

int main(void)
{
    wchar_t output[RU_DIAG_PATH_CAP], exact[8], small[7], long_path[RU_DIAG_PATH_CAP];
    size_t cap, at;
    assert(ru_diag_local_path(L"C:\\"));
    assert(ru_diag_local_path(L"D:\\portable\\目录"));
    assert(ru_diag_local_path(L"C:\\Users\\User\\AppData\\Local\\Temp\\"));
    assert(!ru_diag_local_path(NULL));
    assert(!ru_diag_local_path(L""));
    assert(!ru_diag_local_path(L"C"));
    assert(!ru_diag_local_path(L"C:"));
    assert(!ru_diag_local_path(L"relative\\path"));
    assert(!ru_diag_local_path(L"C:relative"));
    assert(!ru_diag_local_path(L"\\\\server\\share"));
    assert(!ru_diag_local_path(L"\\\\?\\C:\\path"));
    assert(!ru_diag_local_path(L"C:\\foo\\..\\bar"));
    assert(!ru_diag_local_path(L"C:\\foo\\.\\bar"));
    assert(!ru_diag_local_path(L"C:\\foo\\" L"\\bar"));
    assert(!ru_diag_local_path(L"C:\\foo:stream"));
    assert(!ru_diag_local_path(L"C:\\foo/bar"));
    assert(!ru_diag_local_path(L"C:\\foo.\\bar"));
    assert(!ru_diag_local_path(L"C:\\foo "));
    assert(!ru_diag_local_path(L"C:\\foo\nbar"));
    assert(ru_diag_join(exact, 8u, L"C:\\", L"test"));
    assert(wcscmp(exact, L"C:\\test") == 0);
    assert(!ru_diag_join(small, 7u, L"C:\\", L"test"));
    assert(small[0] == L'\0');
    assert(!ru_diag_join(output, 1u, L"C:\\", L"test"));
    assert(output[0] == L'\0');
    assert(!ru_diag_join(output, RU_DIAG_PATH_CAP, L"", L"test"));
    assert(!ru_diag_join(output, RU_DIAG_PATH_CAP, L"C:\\", L""));
    assert(ru_diag_log_path(output, RU_DIAG_PATH_CAP, L"C:\\logs", 42u, 1u, 2u, 0u));
    assert(wcscmp(output, L"C:\\logs\\ru_notepad-0000002a-0000000100000002-00.log") == 0);
    assert(ru_diag_log_path(output, RU_DIAG_PATH_CAP, L"C:\\", 42u, 1u, 2u, 63u));
    assert(!ru_diag_log_path(output, RU_DIAG_PATH_CAP, L"C:\\", 42u, 1u, 2u, 64u));
    assert(output[0] == L'\0');
    assert(!ru_diag_log_path(output, RU_DIAG_PATH_CAP, L"\\\\server\\share", 1u, 2u, 3u, 0u));
    assert(ru_diag_log_path(output, RU_DIAG_PATH_CAP, L"C:\\", ULONG_MAX, ULONG_MAX, ULONG_MAX, 63u));
    for (cap = 0u; cap < 128u; ++cap) {
        wmemset(output, L'!', RU_DIAG_PATH_CAP);
        (void)ru_diag_log_path(output, cap, L"C:\\logs", 1u, 2u, 3u, 0u);
        for (at = cap; at < RU_DIAG_PATH_CAP; ++at) assert(output[at] == L'!');
    }
    wmemset(long_path, L'x', RU_DIAG_PATH_CAP);
    long_path[0] = L'C'; long_path[1] = L':'; long_path[2] = L'\\';
    long_path[RU_DIAG_PATH_CAP - 1u] = L'\0';
    assert(!ru_diag_log_path(output, RU_DIAG_PATH_CAP, long_path, 1u, 2u, 3u, 0u));
    assert(output[0] == L'\0');
    assert(!ru_diag_should_show_failure(0, 0, 0));
    assert(!ru_diag_should_show_failure(0, 1, 7));
    assert(ru_diag_should_show_failure(1, 0, 0));
    assert(!ru_diag_should_show_failure(1, 1, 0));
    assert(ru_diag_should_show_failure(1, 1, 7));
    assert(ru_diag_should_show_failure(1, 1, -1));
    puts("Diagnostic launcher portable path policy passed.");
    return 0;
}
