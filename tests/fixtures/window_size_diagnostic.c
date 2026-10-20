/* Measurement-only hidden Win32 windows. No editor, user files, or UI capture.
 * Matches src/main.ru minimum-track policy and tests/app_i18n_native.ru's two
 * corrections, with one separate test-owned max-track control. Resource 1 is
 * the unchanged packaging/app.manifest, linked by the diagnostic runner. */
#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define WINDOW_STYLE ((DWORD)13565952)
#define MAX_EVENTS 64
#define STAGES 8
#define MAX_TRACK 4096

typedef struct {
    int stage;
    MINMAXINFO before, after;
} MinMaxEvent;
typedef struct {
    int stage, target_width, iteration;
    int requested_width, requested_height;
    RECT outer, client, monitor, work;
    POINT client_screen;
    DWORD style, exstyle;
    UINT dpi;
    int visible, menu_count, callback_count;
} State;
typedef struct {
    State states[STAGES];
    MinMaxEvent events[MAX_EVENTS];
    int event_count, overflow;
} Mode;
static Mode modes[2];
static int policy, current_stage;

typedef UINT (WINAPI *DpiForWindow)(HWND);

static LRESULT CALLBACK window_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (msg == WM_GETMINMAXINFO) {
        MINMAXINFO *m = (MINMAXINFO *)lp;
        Mode *mode = &modes[policy];
        MINMAXINFO before = *m;
        m->ptMinTrackSize.x = 640;
        m->ptMinTrackSize.y = 400;
        if (policy == 1) {
            if (m->ptMaxTrackSize.x < MAX_TRACK) m->ptMaxTrackSize.x = MAX_TRACK;
            if (m->ptMaxTrackSize.y < MAX_TRACK) m->ptMaxTrackSize.y = MAX_TRACK;
        }
        if (mode->event_count == MAX_EVENTS) mode->overflow = 1;
        else {
            MinMaxEvent *event = &mode->events[mode->event_count++];
            event->stage = current_stage;
            event->before = before;
            event->after = *m;
        }
        return 0; /* Same return as the production callback. */
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static int snapshot(HWND hwnd, State *s, DpiForWindow get_dpi) {
    MONITORINFO info;
    HMONITOR monitor = MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST);
    memset(&info, 0, sizeof(info));
    info.cbSize = sizeof(info);
    s->client_screen.x = s->client_screen.y = 0;
    if (!GetWindowRect(hwnd, &s->outer) || !GetClientRect(hwnd, &s->client) ||
        !ClientToScreen(hwnd, &s->client_screen) || !monitor ||
        !GetMonitorInfoW(monitor, &info)) return 0;
    s->monitor = info.rcMonitor;
    s->work = info.rcWork;
    s->style = (DWORD)GetWindowLongPtrW(hwnd, GWL_STYLE);
    s->exstyle = (DWORD)GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    s->visible = IsWindowVisible(hwnd) != 0;
    s->menu_count = GetMenu(hwnd) ? GetMenuItemCount(GetMenu(hwnd)) : 0;
    s->dpi = get_dpi ? get_dpi(hwnd) : 0;
    s->callback_count = modes[policy].event_count;
    return !modes[policy].overflow;
}

static HMENU create_menu(void) {
    static const wchar_t *labels[9] = {
        L"&File", L"&Edit", L"&Search", L"E&ncoding", L"&Language",
        L"&View", L"Se&ttings", L"&UI language", L"&Help"
    };
    HMENU menu = CreateMenu();
    int i;
    if (!menu) return NULL;
    for (i = 0; i < 9; ++i) {
        HMENU sub = CreatePopupMenu();
        if (!sub) { DestroyMenu(menu); return NULL; }
        if (!AppendMenuW(menu, MF_POPUP, (UINT_PTR)sub, labels[i])) {
            DestroyMenu(sub); DestroyMenu(menu); return NULL;
        }
    }
    return menu;
}

static int measure_mode(HINSTANCE instance, DpiForWindow get_dpi) {
    static const int widths[3] = {640, 900, 1600};
    HWND hwnd;
    HMENU menu;
    int w, iteration, ok = 0;
    current_stage = 0;
    hwnd = CreateWindowExW(0, L"RuNotepad.SizeDiagnostic", L"", WINDOW_STYLE,
                          CW_USEDEFAULT, CW_USEDEFAULT, 1120, 760,
                          NULL, NULL, instance, NULL);
    if (!hwnd) return 0;
    modes[policy].states[0].requested_width = 1120;
    modes[policy].states[0].requested_height = 760;
    if (!snapshot(hwnd, &modes[policy].states[0], get_dpi)) goto cleanup;
    menu = create_menu();
    if (!menu) goto cleanup;
    current_stage = 1;
    modes[policy].states[1].stage = 1;
    if (!SetMenu(hwnd, menu)) { DestroyMenu(menu); goto cleanup; }
    if (!DrawMenuBar(hwnd) || !snapshot(hwnd, &modes[policy].states[1], get_dpi)) goto cleanup;
    for (w = 0; w < 3; ++w) {
        for (iteration = 1; iteration <= 2; ++iteration) {
            RECT outer, client;
            State *s;
            current_stage = 2 + w * 2 + iteration - 1;
            s = &modes[policy].states[current_stage];
            s->stage = current_stage;
            s->target_width = widths[w];
            s->iteration = iteration;
            if (!GetWindowRect(hwnd, &outer) || !GetClientRect(hwnd, &client)) goto cleanup;
            s->requested_width = widths[w] + outer.right - outer.left - client.right + client.left;
            s->requested_height = 720 + outer.bottom - outer.top - client.bottom + client.top;
            if (!MoveWindow(hwnd, 40, 40, s->requested_width, s->requested_height, TRUE) ||
                !snapshot(hwnd, s, get_dpi)) goto cleanup;
        }
    }
    ok = modes[policy].event_count > 0 && !modes[policy].overflow;
cleanup:
    /* DestroyWindow owns the assigned menu. Windows remain hidden throughout. */
    if (!DestroyWindow(hwnd)) ok = 0;
    return ok;
}

static void print_rect(const RECT *r) {
    printf("[%ld,%ld,%ld,%ld]", r->left, r->top, r->right, r->bottom);
}
static void print_minmax(const MINMAXINFO *m) {
    printf("[%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld]",
           m->ptReserved.x, m->ptReserved.y, m->ptMaxSize.x, m->ptMaxSize.y,
           m->ptMaxPosition.x, m->ptMaxPosition.y, m->ptMinTrackSize.x,
           m->ptMinTrackSize.y, m->ptMaxTrackSize.x, m->ptMaxTrackSize.y);
}

int main(int argc, char **argv) {
    WNDCLASSEXW wc;
    HINSTANCE instance = GetModuleHandleW(NULL);
    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    DpiForWindow get_dpi;
    FARPROC address = user32 ? GetProcAddress(user32, "GetDpiForWindow") : NULL;
    RECT work;
    HDC dc;
    int dpi_x, dpi_y, p, i;
    (void)argv;
    /* No input paths or configurable capture. Reject any unexpected argument. */
    if (argc != 1 || sizeof(void *) != 8 || !instance) return 10;
    _Static_assert(sizeof(get_dpi) == sizeof(address), "function pointer size");
    memcpy(&get_dpi, &address, sizeof(get_dpi));
    if (!SystemParametersInfoW(SPI_GETWORKAREA, 0, &work, 0)) return 11;
    dc = GetDC(NULL);
    if (!dc) return 12;
    dpi_x = GetDeviceCaps(dc, LOGPIXELSX);
    dpi_y = GetDeviceCaps(dc, LOGPIXELSY);
    if (!ReleaseDC(NULL, dc)) return 13;
    memset(&wc, 0, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = window_proc;
    wc.hInstance = instance;
    wc.lpszClassName = L"RuNotepad.SizeDiagnostic";
    if (!RegisterClassExW(&wc)) return 14;
    for (policy = 0; policy < 2; ++policy) {
        if (!measure_mode(instance, get_dpi)) return 15 + policy;
    }
    if (!UnregisterClassW(wc.lpszClassName, instance)) return 17;
    /* Publish only after all measurements succeed; no paths, titles, handles,
       device names, screenshots, application content, or environment strings. */
    printf("{\"schema\":1,\"system\":{\"screen\":[%d,%d],\"virtual_screen\":[%d,%d,%d,%d],",
           GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN),
           GetSystemMetrics(SM_XVIRTUALSCREEN), GetSystemMetrics(SM_YVIRTUALSCREEN),
           GetSystemMetrics(SM_CXVIRTUALSCREEN), GetSystemMetrics(SM_CYVIRTUALSCREEN));
    printf("\"work\":"); print_rect(&work);
    printf(",\"max_track\":[%d,%d],\"min_track\":[%d,%d],\"maximized\":[%d,%d],",
           GetSystemMetrics(SM_CXMAXTRACK), GetSystemMetrics(SM_CYMAXTRACK),
           GetSystemMetrics(SM_CXMINTRACK), GetSystemMetrics(SM_CYMINTRACK),
           GetSystemMetrics(SM_CXMAXIMIZED), GetSystemMetrics(SM_CYMAXIMIZED));
    printf("\"dpi_aware\":%d,\"device_dpi\":[%d,%d],\"pointer_bits\":64,\"compiled_style\":%lu,\"override_max_track\":[4096,4096]},\"modes\":[",
           IsProcessDPIAware() != 0, dpi_x, dpi_y, (unsigned long)WINDOW_STYLE);
    for (p = 0; p < 2; ++p) {
        Mode *mode = &modes[p];
        printf("%s{\"policy\":%d,\"states\":[", p ? "," : "", p);
        for (i = 0; i < STAGES; ++i) {
            State *s = &mode->states[i];
            printf("%s{\"stage\":%d,\"target_width\":%d,\"target_height\":%d,\"iteration\":%d,\"requested_outer\":[%d,%d],\"outer\":",
                   i ? "," : "", s->stage, s->target_width, i >= 2 ? 720 : 0,
                   s->iteration, s->requested_width, s->requested_height);
            print_rect(&s->outer); printf(",\"client\":"); print_rect(&s->client);
            printf(",\"client_screen\":[%ld,%ld],\"style\":%lu,\"exstyle\":%lu,\"visible\":%d,\"dpi\":%u,\"menu_count\":%d,\"callback_count\":%d,\"monitor\":",
                   s->client_screen.x, s->client_screen.y, (unsigned long)s->style,
                   (unsigned long)s->exstyle, s->visible, s->dpi, s->menu_count, s->callback_count);
            print_rect(&s->monitor); printf(",\"work\":"); print_rect(&s->work); printf("}");
        }
        printf("],\"minmax\":[");
        for (i = 0; i < mode->event_count; ++i) {
            MinMaxEvent *e = &mode->events[i];
            printf("%s{\"stage\":%d,\"before\":", i ? "," : "", e->stage);
            print_minmax(&e->before); printf(",\"after\":"); print_minmax(&e->after); printf("}");
        }
        printf("]}");
    }
    printf("]}\n");
    return ferror(stdout) ? 18 : 0;
}
