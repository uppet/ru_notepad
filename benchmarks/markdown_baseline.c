/* RESEARCH ONLY: fixed native Windows baseline, never part of the application.
 * The final fold oracle is predetermined, NOT a C Markdown parser. All calls
 * use ordinary same-thread SendMessageW. No Ru runtime or file-drop callback.
 * Validation and teardown are outside every timer. See the accompanying doc.
 */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "Scintilla.h"

#define INPUT_BYTES 1000000
#define INPUT_LINES 100001
#define CLIENT_WIDTH 960
#define CLIENT_HEIGHT 640
#define MAX_SECONDS 15
#define FNV_OFFSET UINT64_C(14695981039346656037)
#define FNV_PRIME UINT64_C(1099511628211)
#define STYLE_HASH UINT64_C(0xf3e8304ab5c43d36)
#define FINAL_FOLD_HASH UINT64_C(0x14a0b025819607a9)
#define DEFAULT_FOLD_HASH UINT64_C(0x08c4ea94396a8f49)

typedef void *(__cdecl *CreateLexerFn)(const char *);
typedef struct {
    HWND parent, editor;
    WNDPROC original;
    int observe_paint, paints, full_paints, bad_paint;
} Editor;
typedef struct {
    const char *component;
    LONGLONG start, end;
    LONGLONG read_ticks, setup_ticks, load_ticks, style_ticks, fold_ticks, paint_ticks;
    uint64_t style_hash, fold_hash;
    int final_folds, paint_count;
} Result;
static LARGE_INTEGER frequency;
static CreateLexerFn create_lexer;
static HINSTANCE instance;

static void require(int condition, const char *code) {
    if (!condition) {
        /* Static codes only: never emit paths, document text or system errors. */
        fprintf(stderr, "MD_NATIVE_ERROR %s\n", code);
        ExitProcess(1);
    }
}
static LONGLONG qpc(void) {
    LARGE_INTEGER value;
    require(QueryPerformanceCounter(&value) && value.QuadPart > 0, "qpc_read");
    return value.QuadPart;
}
static LONGLONG delta(LONGLONG begin, LONGLONG end) {
    require(begin > 0 && end > begin && end - begin <= frequency.QuadPart * MAX_SECONDS,
            "qpc_interval");
    return end - begin;
}
static LRESULT sci(HWND editor, UINT message, WPARAM wparam, LPARAM lparam) {
    return SendMessageW(editor, message, wparam, lparam);
}
static unsigned char expected_byte(size_t offset) {
    static const char head[] = "# Heading\n\n~~~\n";
    static const char fill[] = "code text\n";
    static const char tail[] = "codebody";
    if (offset < sizeof(head) - 1) return (unsigned char)head[offset];
    if (offset >= INPUT_BYTES - (sizeof(tail) - 1))
        return (unsigned char)tail[offset - (INPUT_BYTES - (sizeof(tail) - 1))];
    return (unsigned char)fill[(offset - (sizeof(head) - 1)) % (sizeof(fill) - 1)];
}
static unsigned char expected_style(size_t offset) {
    if (offset == 0) return 6;
    if (offset == 9 || offset == 10) return 1;
    return offset < 11 ? 0 : 21;
}
static int expected_fold(size_t line, int final_folds) {
    return final_folds ? (line == 0 ? 9216 : 1025) : 1024;
}
static void local_path(wchar_t *destination, const wchar_t *name) {
    DWORD size = GetModuleFileNameW(NULL, destination, 32768);
    wchar_t *last;
    require(size > 0 && size < 32767, "module_path");
    last = wcsrchr(destination, L'\\');
    require(last != NULL && (size_t)(last - destination) + wcslen(name) + 2 < 32768,
            "module_path");
    wcscpy(last + 1, name);
}
static char *read_input(void) {
    wchar_t path[32768];
    HANDLE file;
    LARGE_INTEGER length;
    DWORD count;
    BY_HANDLE_FILE_INFORMATION info;
    char *text = (char *)malloc(INPUT_BYTES + 1);
    require(text != NULL, "input_allocation");
    local_path(path, L"fixture.md");
    file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                       FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, NULL);
    require(file != INVALID_HANDLE_VALUE, "input_open");
    require(GetFileInformationByHandle(file, &info) && info.nNumberOfLinks == 1 &&
            !(info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)),
            "input_type");
    require(GetFileSizeEx(file, &length) && length.QuadPart == INPUT_BYTES, "input_size");
    require(ReadFile(file, text, INPUT_BYTES, &count, NULL) && count == INPUT_BYTES,
            "input_read");
    require(CloseHandle(file), "input_close");
    text[INPUT_BYTES] = 0;
    return text;
}
static LRESULT CALLBACK parent_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    return DefWindowProcW(hwnd, msg, wp, lp);
}
static LRESULT CALLBACK paint_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    Editor *owner = (Editor *)GetWindowLongPtrW(hwnd, GWLP_USERDATA);
    require(owner != NULL && owner->original != NULL, "paint_owner");
    if (msg == WM_PAINT && owner->observe_paint) {
        RECT client;
        HRGN pending = CreateRectRgn(0, 0, 0, 0), entire;
        int kind, full;
        require(pending != NULL && GetClientRect(hwnd, &client), "paint_region");
        entire = CreateRectRgnIndirect(&client);
        require(entire != NULL, "paint_region");
        kind = GetUpdateRgn(hwnd, pending, FALSE);
        full = kind != ERROR && kind != NULLREGION && EqualRgn(pending, entire);
        require(DeleteObject(pending) && DeleteObject(entire), "paint_region_cleanup");
        ++owner->paints;
        owner->full_paints += !!full;
        if (!full) owner->bad_paint = 1;
    }
    return CallWindowProcW(owner->original, hwnd, msg, wp, lp);
}
static void create_editor(Editor *owner, int observe) {
    RECT frame = {0, 0, CLIENT_WIDTH, CLIENT_HEIGHT};
    void *lexer;
    sptr_t doc;
    int style;
    static const int palette[][2] = {
        {2,12934144},{3,12934144},{4,12665455},{5,12665455},{6,12934144},
        {7,12934144},{8,12934144},{9,12934144},{10,12934144},{11,12934144},
        {13,2514553},{14,2514553},{15,3573283},{16,8421504},{17,4473924},
        {18,12665455},{19,1381795},{20,1381795},{21,1381795}
    };
    memset(owner, 0, sizeof(*owner));
    require(AdjustWindowRectEx(&frame, WS_OVERLAPPEDWINDOW, FALSE, 0), "frame_size");
    owner->parent = CreateWindowExW(0, L"MarkdownNativeBaseline", L"Native Markdown baseline",
        WS_OVERLAPPEDWINDOW, 20, 20, frame.right - frame.left, frame.bottom - frame.top,
        NULL, NULL, instance, NULL);
    require(owner->parent != NULL, "parent_create");
    owner->editor = CreateWindowExW(0, L"Scintilla", L"", WS_CHILD | WS_VISIBLE | WS_TABSTOP,
        0, 0, CLIENT_WIDTH, CLIENT_HEIGHT, owner->parent, NULL, instance, NULL);
    require(owner->editor != NULL, "editor_create");
    require(GetDpiForWindow(owner->editor) == 96, "dpi_not_96");
    doc = sci(owner->editor, SCI_CREATEDOCUMENT, 0, SC_DOCUMENTOPTION_TEXT_LARGE);
    require(doc != 0, "document_create");
    sci(owner->editor, SCI_SETDOCPOINTER, 0, doc);
    sci(owner->editor, SCI_RELEASEDOCUMENT, 0, doc);
    sci(owner->editor, SCI_SETCODEPAGE, SC_CP_UTF8, 0);
    sci(owner->editor, SCI_STYLESETFONT, STYLE_DEFAULT, (LPARAM)"Consolas");
    sci(owner->editor, SCI_STYLESETSIZE, STYLE_DEFAULT, 11);
    sci(owner->editor, SCI_STYLESETFORE, STYLE_DEFAULT, 2039583);
    sci(owner->editor, SCI_STYLESETBACK, STYLE_DEFAULT, 16777215);
    sci(owner->editor, SCI_STYLECLEARALL, 0, 0);
    sci(owner->editor, SCI_SETMARGINTYPEN, 0, SC_MARGIN_NUMBER);
    sci(owner->editor, SCI_SETMARGINWIDTHN, 0, 56);
    sci(owner->editor, SCI_SETMARGINTYPEN, 2, SC_MARGIN_SYMBOL);
    sci(owner->editor, SCI_SETMARGINMASKN, 2, SC_MASK_FOLDERS);
    sci(owner->editor, SCI_SETMARGINWIDTHN, 2, 20);
    sci(owner->editor, SCI_SETWRAPMODE, SC_WRAP_NONE, 0);
    sci(owner->editor, SCI_SETHSCROLLBAR, 0, 0);
    sci(owner->editor, SCI_SETVSCROLLBAR, 0, 0);
    sci(owner->editor, SCI_SETTECHNOLOGY, SC_TECHNOLOGY_DEFAULT, 0);
    sci(owner->editor, SCI_SETAUTOMATICFOLD, 0, 0);
    sci(owner->editor, SCI_SETMODEVENTMASK, SC_MOD_INSERTTEXT | SC_MOD_DELETETEXT, 0);
    sci(owner->editor, SCI_SETIDLESTYLING, SC_IDLESTYLING_NONE, 0);
    lexer = create_lexer("markdown");
    require(lexer != NULL, "lexer_create");
    sci(owner->editor, SCI_SETILEXER, 0, (LPARAM)lexer); /* Ownership transferred. */
    sci(owner->editor, SCI_SETPROPERTY, (WPARAM)"fold", (LPARAM)"0");
    for (style = 0; style < (int)(sizeof(palette) / sizeof(palette[0])); ++style)
        sci(owner->editor, SCI_STYLESETFORE, palette[style][0], palette[style][1]);
    require(sci(owner->editor, SCI_GETLEXER, 0, 0) == 98 &&
            sci(owner->editor, SCI_GETSTATUS, 0, 0) == 0, "editor_setup");
    if (observe) {
        SetLastError(0);
        require(SetWindowLongPtrW(owner->editor, GWLP_USERDATA, (LONG_PTR)owner) != 0 ||
                GetLastError() == 0, "paint_userdata");
        owner->original = (WNDPROC)SetWindowLongPtrW(owner->editor, GWLP_WNDPROC, (LONG_PTR)paint_proc);
        require(owner->original != NULL, "paint_subclass");
    }
}
static void load_editor(Editor *owner, const char *text) {
    sci(owner->editor, SCI_SETUNDOCOLLECTION, 0, 0);
    sci(owner->editor, SCI_ADDTEXT, INPUT_BYTES, (LPARAM)text);
    sci(owner->editor, SCI_EMPTYUNDOBUFFER, 0, 0);
    sci(owner->editor, SCI_SETUNDOCOLLECTION, 1, 0);
    sci(owner->editor, SCI_SETSAVEPOINT, 0, 0);
    sci(owner->editor, SCI_SETSEL, 2, 19);
    require(sci(owner->editor, SCI_GETLENGTH, 0, 0) == INPUT_BYTES &&
            sci(owner->editor, SCI_GETENDSTYLED, 0, 0) == 0, "load_precondition");
}
static void colourise(Editor *owner) {
    sci(owner->editor, SCI_COLOURISE, 0, -1);
}
static void write_folds(Editor *owner) {
    size_t line;
    for (line = 0; line < INPUT_LINES; ++line)
        sci(owner->editor, SCI_SETFOLDLEVEL, line, expected_fold(line, 1));
}
static void default_folds(Editor *owner) {
    size_t line;
    for (line = 0; line < INPUT_LINES; ++line)
        require(sci(owner->editor, SCI_GETFOLDLEVEL, line, 0) == 1024, "initial_fold");
}
static void verify(Editor *owner, Result *result, const char *input) {
    struct Sci_TextRangeFull range;
    unsigned char *styled = (unsigned char *)malloc(INPUT_BYTES * 2 + 2);
    uint64_t styles = FNV_OFFSET, folds = FNV_OFFSET;
    size_t i, lf = 0;
    RECT client;
    char font[128] = {0};
    require(styled != NULL, "validation_allocation");
    range.chrg.cpMin = 0; range.chrg.cpMax = INPUT_BYTES; range.lpstrText = (char *)styled;
    require(sci(owner->editor, SCI_GETSTYLEDTEXTFULL, 0, (LPARAM)&range) == INPUT_BYTES * 2,
            "styled_read");
    for (i = 0; i < INPUT_BYTES; ++i) {
        require((unsigned char)input[i] == expected_byte(i) && styled[i * 2] == expected_byte(i),
                "text_byte");
        require(styled[i * 2 + 1] == expected_style(i), "style_byte");
        styles = (styles ^ styled[i * 2 + 1]) * FNV_PRIME;
        lf += input[i] == '\n';
    }
    require(lf == 100000, "newline_count");
    for (i = 0; i < INPUT_LINES; ++i) {
        uint32_t level = (uint32_t)sci(owner->editor, SCI_GETFOLDLEVEL, i, 0);
        int byte;
        require(level == (uint32_t)expected_fold(i, result->final_folds), "fold_line");
        require(sci(owner->editor, SCI_GETLINEVISIBLE, i, 0) == 1 &&
                sci(owner->editor, SCI_GETFOLDEXPANDED, i, 0) == 1, "line_visibility");
        for (byte = 0; byte < 4; ++byte) folds = (folds ^ ((level >> (byte * 8)) & 255)) * FNV_PRIME;
    }
    require(styles == STYLE_HASH && folds == (result->final_folds ? FINAL_FOLD_HASH : DEFAULT_FOLD_HASH),
            "oracle_hash");
    require(sci(owner->editor, SCI_GETLENGTH, 0, 0) == INPUT_BYTES &&
            sci(owner->editor, SCI_GETLINECOUNT, 0, 0) == INPUT_LINES &&
            sci(owner->editor, SCI_GETENDSTYLED, 0, 0) == INPUT_BYTES &&
            sci(owner->editor, SCI_GETMODIFY, 0, 0) == 0 &&
            sci(owner->editor, SCI_GETANCHOR, 0, 0) == 2 &&
            sci(owner->editor, SCI_GETCURRENTPOS, 0, 0) == 19 &&
            sci(owner->editor, SCI_CANUNDO, 0, 0) == 0 &&
            sci(owner->editor, SCI_CANREDO, 0, 0) == 0 &&
            sci(owner->editor, SCI_GETUNDOCOLLECTION, 0, 0) == 1 &&
            sci(owner->editor, SCI_GETSTATUS, 0, 0) == 0, "editor_state");
    require(GetClientRect(owner->editor, &client) && client.right == CLIENT_WIDTH &&
            client.bottom == CLIENT_HEIGHT, "client_size");
    sci(owner->editor, SCI_STYLEGETFONT, STYLE_DEFAULT, (LPARAM)font);
    require(strcmp(font, "Consolas") == 0 &&
            sci(owner->editor, SCI_STYLEGETSIZE, STYLE_DEFAULT, 0) == 11 &&
            sci(owner->editor, SCI_GETWRAPMODE, 0, 0) == SC_WRAP_NONE &&
            sci(owner->editor, SCI_GETHSCROLLBAR, 0, 0) == 0 &&
            sci(owner->editor, SCI_GETVSCROLLBAR, 0, 0) == 0 &&
            sci(owner->editor, SCI_GETTECHNOLOGY, 0, 0) == SC_TECHNOLOGY_DEFAULT &&
            sci(owner->editor, SCI_GETCODEPAGE, 0, 0) == SC_CP_UTF8 &&
            sci(owner->editor, SCI_GETAUTOMATICFOLD, 0, 0) == 0 &&
            sci(owner->editor, SCI_GETPROPERTYINT, (WPARAM)"fold", 0) == 0 &&
            GetDpiForWindow(owner->editor) == 96, "presentation_state");
    result->style_hash = styles; result->fold_hash = folds;
    free(styled);
}
static void destroy_editor(Editor *owner) {
    if (owner->original) {
        require((WNDPROC)SetWindowLongPtrW(owner->editor, GWLP_WNDPROC, (LONG_PTR)owner->original)
                == paint_proc, "paint_unsubclass");
    }
    require(DestroyWindow(owner->editor) && DestroyWindow(owner->parent), "window_cleanup");
    memset(owner, 0, sizeof(*owner));
}
static int paint_region_empty(HWND editor) {
    HRGN region = CreateRectRgn(0, 0, 0, 0);
    int kind;
    require(region != NULL, "paint_region");
    kind = GetUpdateRgn(editor, region, FALSE);
    require(DeleteObject(region), "paint_region_cleanup");
    require(kind != ERROR, "paint_region_read");
    return kind == NULLREGION;
}
static void measure_component(Result *result, int component) {
    Editor owner;
    char *input;
    LONGLONG last, next;
    memset(result, 0, sizeof(*result));
    result->component = component == 0 ? "colourise" : component == 1 ? "fold_writes" : "read_to_paint";
    result->final_folds = component != 0;
    if (component != 2) {
        input = read_input();
        create_editor(&owner, 0);
        load_editor(&owner, input);
        default_folds(&owner);
        if (component == 1) {
            colourise(&owner);
            default_folds(&owner);
            require(sci(owner.editor, SCI_GETENDSTYLED, 0, 0) == INPUT_BYTES, "fold_style_precondition");
        }
        result->start = qpc();
        if (component == 0) colourise(&owner); else write_folds(&owner);
        result->end = qpc();
        if (component == 0) result->style_ticks = delta(result->start, result->end);
        else result->fold_ticks = delta(result->start, result->end);
    } else {
        result->start = last = qpc();
        input = read_input();
        next = qpc(); result->read_ticks = delta(last, next); last = next;
        create_editor(&owner, 1);
        next = qpc(); result->setup_ticks = delta(last, next); last = next;
        load_editor(&owner, input);
        next = qpc(); result->load_ticks = delta(last, next); last = next;
        colourise(&owner);
        next = qpc(); result->style_ticks = delta(last, next); last = next;
        write_folds(&owner);
        next = qpc(); result->fold_ticks = delta(last, next); last = next;
        owner.observe_paint = 1;
        require(RedrawWindow(owner.editor, NULL, NULL, RDW_INVALIDATE | RDW_ERASE), "paint_invalidate");
        ShowWindow(owner.parent, SW_SHOWNOACTIVATE);
        require(IsWindowVisible(owner.editor), "paint_visible");
        require(UpdateWindow(owner.editor) && GdiFlush(), "paint_update");
        result->end = qpc(); result->paint_ticks = delta(last, result->end);
        owner.observe_paint = 0;
        require(owner.paints == 1 && owner.full_paints == 1 && !owner.bad_paint &&
                paint_region_empty(owner.editor), "paint_completion");
        result->paint_count = owner.paints;
    }
    delta(result->start, result->end);
    verify(&owner, result, input);
    destroy_editor(&owner);
    free(input);
}
int main(int argc, char **argv) {
    wchar_t path[32768];
    HMODULE scintilla, lexilla;
    FARPROC export_address;
    WNDCLASSW klass;
    Result results[3];
    int i, run;
    require(argc == 3 && strcmp(argv[1], "--run") == 0 && strlen(argv[2]) == 1 &&
            argv[2][0] >= '1' && argv[2][0] <= '3', "arguments");
    run = argv[2][0] - '0';
    require(sizeof(void *) == 8 && sizeof(Sci_Position) == 8, "x64_required");
    require(QueryPerformanceFrequency(&frequency) && frequency.QuadPart > 0 &&
            frequency.QuadPart <= 1000000000, "qpc_frequency");
    require(SetProcessDPIAware(), "dpi_setup");
    instance = GetModuleHandleW(NULL);
    local_path(path, L"Scintilla.dll");
    scintilla = LoadLibraryExW(path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    require(scintilla != NULL, "scintilla_load");
    local_path(path, L"Lexilla.dll");
    lexilla = LoadLibraryExW(path, NULL, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    require(lexilla != NULL, "lexilla_load");
    export_address = GetProcAddress(lexilla, "CreateLexer");
    require(export_address != NULL && sizeof(export_address) == sizeof(create_lexer), "lexer_export");
    memcpy(&create_lexer, &export_address, sizeof(create_lexer));
    memset(&klass, 0, sizeof(klass));
    klass.lpfnWndProc = parent_proc; klass.hInstance = instance;
    klass.lpszClassName = L"MarkdownNativeBaseline";
    require(RegisterClassW(&klass) != 0, "class_register");
    for (i = 0; i < 3; ++i) measure_component(&results[i], i);
    require(UnregisterClassW(klass.lpszClassName, instance) && FreeLibrary(lexilla) &&
            FreeLibrary(scintilla), "library_cleanup");
    printf("{\"schema\":1,\"run\":%d,\"qpc_frequency\":%lld,\"client_width\":960,\"client_height\":640,"
           "\"dpi\":96,\"font\":\"Consolas\",\"font_points\":11,\"wrap\":\"none\","
           "\"scrollbars\":false,\"technology\":\"gdi\",\"cleanup\":true,\"components\":[",
           run, (long long)frequency.QuadPart);
    for (i = 0; i < 3; ++i) {
        Result *r = &results[i];
        printf("%s{\"component\":\"%s\",\"qpc_start\":%lld,\"qpc_end\":%lld,"
            "\"read_ticks\":%lld,\"setup_ticks\":%lld,\"load_ticks\":%lld,\"style_ticks\":%lld,"
            "\"fold_ticks\":%lld,\"paint_ticks\":%lld,\"verified_bytes\":1000000,\"verified_lines\":100001,"
            "\"style_fnv1a64\":\"%016llx\",\"fold_fnv1a64\":\"%016llx\","
            "\"fold_mode\":\"%s\",\"fold_writes\":%d,\"paint_count\":%d,"
            "\"dirty\":false,\"anchor\":2,\"caret\":19,\"can_undo\":false,\"can_redo\":false,"
            "\"undo_collection\":true,\"all_visible\":true,\"all_expanded\":true,\"end_styled\":1000000}",
            i ? "," : "", r->component, (long long)r->start, (long long)r->end,
            (long long)r->read_ticks, (long long)r->setup_ticks, (long long)r->load_ticks,
            (long long)r->style_ticks, (long long)r->fold_ticks, (long long)r->paint_ticks,
            (unsigned long long)r->style_hash, (unsigned long long)r->fold_hash,
            r->final_folds ? "predetermined_final" : "untouched_default", r->final_folds ? INPUT_LINES : 0,
            r->paint_count);
    }
    printf("]}\n");
    return fflush(stdout) == 0 ? 0 : 1;
}
