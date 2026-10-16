@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ERRORLEVEL="
cd /d "%~dp0"
set "TESTDIR=%CD%\selftest-%RANDOM%-%RANDOM%"
mkdir "%TESTDIR%" || exit /b 1
>test-results.txt echo ru_notepad portable console self-tests - synthetic files only
>>test-results.txt echo ru_notepad.exe: interactive editor; CI separately checks detached GUI startup, Unicode file entry, Ru styling/folding and normal close.
>>test-results.txt echo RuSyntaxWrongAbi.dll: test-only ABI-mismatch fixture; never replace the ordinary RuSyntax.dll with it.
>>test-results.txt echo file_codec_security_probe.exe: helper for optional-acl-tests.ps1; never run it against important files.
>>test-results.txt echo Optional NTFS ACL cases are described in OPTIONAL-ACL-TESTS.txt and run separately.
>>test-results.txt echo Full tests include a real 500039680-byte editor load/save: allow 3 GiB RAM, 2 GiB free disk, and 15 minutes.
>>test-results.txt ver
set "FAILED=0"
>>test-results.txt echo document_policy.exe: document limits, dirty-state and safe-save policy.
document_policy.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ui_arguments.exe: GUI argument values and numeric flag construction.
ui_arguments.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo file_codec_flags.exe: numeric file-attribute predicates and grouping regressions.
file_codec_flags.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo editor_native.exe: Scintilla text, selection, search and undo integration.
editor_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_native.exe: real C/C++ and JSON token styling, Unicode offsets and editor-state preservation.
syntax_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_policy.exe: exact suffix and argument-array matching through the production policy.
syntax_policy.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_lexical_policy.exe: pinned Ru tokenization, UTF-8 byte offsets, multiline state and nested folding policy.
ru_lexical_policy.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_syntax_native.exe: real Scintilla Ru styles, edits, folding, margin callbacks and bounded performance probes.
ru_syntax_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo app_ru_native.exe: actual Ru language menu routing, fold commands, tab isolation and unchanged document state.
app_ru_native.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo shortcuts.exe: keyboard shortcut routing and modifier combinations.
shortcuts.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo status_native.exe: caret columns, selections, current-line endings and document metadata.
status_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo app_native.exe: original application lifecycle, tabs and safe close regressions.
app_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo app_features_native.exe: real menu dispatch, language changes, tab isolation, zoom, status and undo.
app_features_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo app_streaming_native.exe: actual main event loop, Unicode entry, busy cancel, dirty tabs and safe staged saves.
app_streaming_native.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo file_codec_tests.exe: synthetic file encoding, lossless saves and failure handling.
file_codec_tests.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo associations_policy.exe: explicit per-user registration commands and quoted Unicode application paths.
associations_policy.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo associations_native.exe: isolated synthetic HKCU registration with cleanup, never actual defaults or UserChoice.
associations_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo file_drop_native.exe: actual Scintilla child WM_DROPFILES routing, Unicode paths, HDROP ownership and callback cleanup.
file_drop_native.exe >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo file_streaming_native.exe: bounded large-file encoding, exact bytes, sparse threshold and pre-read cancellation.
file_streaming_native.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo editor_streaming_native.exe: native editor streaming, Unicode boundaries and full large-file roundtrip.
editor_streaming_native.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo editor_streaming_native.exe --large: mandatory full 500039680-byte native editor load/save and every-byte verification.
editor_streaming_native.exe "%TESTDIR%" --large >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_native.exe --expect-missing: isolated absent-DLL fallback keeps plain-text editing and undo working.
call :syntax_fallback missing-lexilla --expect-missing
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_native.exe --expect-bad-lexer: isolated DLL without CreateLexer falls back without losing text.
call :syntax_fallback bad-lexer --expect-bad-lexer
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_syntax_native.exe --expect-missing-lexilla: isolated Ru styles and folding work without Lexilla.
call :syntax_fallback missing-ru-lexilla --expect-missing-lexilla ru_syntax_native
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_syntax_native.exe --expect-missing-helper: missing helper reports clean plain-text fallback with Lexilla present.
call :syntax_fallback missing-helper --expect-missing-helper ru_syntax_native missing-helper
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_syntax_native.exe --expect-bad-helper: wrong helper exports report clean plain-text fallback.
call :syntax_fallback bad-helper --expect-bad-helper ru_syntax_native bad-helper
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo ru_syntax_native.exe --expect-wrong-helper-abi: compiled wrong-version helper reports clean plain-text fallback.
call :syntax_fallback wrong-helper-abi --expect-wrong-helper-abi ru_syntax_native wrong-helper-abi
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo OVERALL_FAILURE=%FAILED%
type test-results.txt
if "%FAILED%"=="0" (rmdir "%TESTDIR%" 2>nul) else (echo Failed tests may have kept fixtures in "%TESTDIR%".)
echo Results are saved in test-results.txt.
pause
exit /b %FAILED%

:syntax_fallback
set "FALLBACKEXE=%~3"
if not defined FALLBACKEXE set "FALLBACKEXE=syntax_native"
set "FALLBACKDIR=%TESTDIR%\%~1"
mkdir "%FALLBACKDIR%" || exit /b 1
copy /b "%FALLBACKEXE%.exe" "%FALLBACKDIR%\%FALLBACKEXE%.exe" >nul || exit /b 1
copy /b "Scintilla.dll" "%FALLBACKDIR%\Scintilla.dll" >nul || exit /b 1
if "%~4"=="" copy /b "RuSyntax.dll" "%FALLBACKDIR%\RuSyntax.dll" >nul || exit /b 1
if "%~4"=="bad-helper" copy /b "Scintilla.dll" "%FALLBACKDIR%\RuSyntax.dll" >nul || exit /b 1
if "%~4"=="wrong-helper-abi" copy /b "RuSyntaxWrongAbi.dll" "%FALLBACKDIR%\RuSyntax.dll" >nul || exit /b 1
if not "%~4"=="" copy /b "Lexilla.dll" "%FALLBACKDIR%\Lexilla.dll" >nul || exit /b 1
if "%~1"=="bad-lexer" copy /b "Scintilla.dll" "%FALLBACKDIR%\Lexilla.dll" >nul || exit /b 1
pushd "%FALLBACKDIR%" || exit /b 1
"%FALLBACKEXE%.exe" %~2 >>"%~dp0test-results.txt" 2>&1
set "FALLBACK_STATUS=%ERRORLEVEL%"
popd
del /q "%FALLBACKDIR%\%FALLBACKEXE%.exe" "%FALLBACKDIR%\Scintilla.dll"
if exist "%FALLBACKDIR%\RuSyntax.dll" del /q "%FALLBACKDIR%\RuSyntax.dll"
if exist "%FALLBACKDIR%\Lexilla.dll" del /q "%FALLBACKDIR%\Lexilla.dll"
rmdir "%FALLBACKDIR%" 2>nul
exit /b %FALLBACK_STATUS%
