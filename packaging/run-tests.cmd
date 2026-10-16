@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ERRORLEVEL="
cd /d "%~dp0"
set "TESTDIR=%CD%\selftest-%RANDOM%-%RANDOM%"
mkdir "%TESTDIR%" || exit /b 1
>test-results.txt echo ru_notepad portable console self-tests - synthetic files only
>>test-results.txt echo ru_notepad.exe: interactive editor; CI separately checks its detached GUI startup and normal close.
>>test-results.txt echo file_codec_security_probe.exe: helper for optional-acl-tests.ps1; never run it against important files.
>>test-results.txt echo Optional NTFS ACL cases are described in OPTIONAL-ACL-TESTS.txt and run separately.
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
>>test-results.txt echo file_codec_tests.exe: synthetic file encoding, lossless saves and failure handling.
file_codec_tests.exe "%TESTDIR%" >>test-results.txt 2>&1
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_native.exe --expect-missing: isolated absent-DLL fallback keeps plain-text editing and undo working.
call :syntax_fallback missing-lexilla --expect-missing
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo syntax_native.exe --expect-bad-lexer: isolated DLL without CreateLexer falls back without losing text.
call :syntax_fallback bad-lexer --expect-bad-lexer
if not "%ERRORLEVEL%"=="0" set "FAILED=1"
>>test-results.txt echo OVERALL_FAILURE=%FAILED%
type test-results.txt
if "%FAILED%"=="0" (rmdir "%TESTDIR%" 2>nul) else (echo Failed tests may have kept fixtures in "%TESTDIR%".)
echo Results are saved in test-results.txt.
pause
exit /b %FAILED%

:syntax_fallback
set "FALLBACKDIR=%TESTDIR%\%~1"
mkdir "%FALLBACKDIR%" || exit /b 1
copy /b "syntax_native.exe" "%FALLBACKDIR%\syntax_native.exe" >nul || exit /b 1
copy /b "Scintilla.dll" "%FALLBACKDIR%\Scintilla.dll" >nul || exit /b 1
if "%~1"=="bad-lexer" copy /b "Scintilla.dll" "%FALLBACKDIR%\Lexilla.dll" >nul || exit /b 1
pushd "%FALLBACKDIR%" || exit /b 1
syntax_native.exe %~2 >>"%~dp0test-results.txt" 2>&1
set "FALLBACK_STATUS=%ERRORLEVEL%"
popd
del /q "%FALLBACKDIR%\syntax_native.exe" "%FALLBACKDIR%\Scintilla.dll"
if exist "%FALLBACKDIR%\Lexilla.dll" del /q "%FALLBACKDIR%\Lexilla.dll"
rmdir "%FALLBACKDIR%" 2>nul
exit /b %FALLBACK_STATUS%
