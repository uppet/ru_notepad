@echo off
setlocal
cd /d "%~dp0"
set "TESTDIR=%CD%\selftest-%RANDOM%-%RANDOM%"
mkdir "%TESTDIR%" || exit /b 1
>test-results.txt echo ru_notepad native Windows acceptance tests
>>test-results.txt ver
set "FAILED=0"
document_policy.exe >>test-results.txt 2>&1
if errorlevel 1 set "FAILED=1"
ui_arguments.exe >>test-results.txt 2>&1
if errorlevel 1 set "FAILED=1"
editor_native.exe >>test-results.txt 2>&1
if errorlevel 1 set "FAILED=1"
app_native.exe >>test-results.txt 2>&1
if errorlevel 1 set "FAILED=1"
file_codec_tests.exe "%TESTDIR%" >>test-results.txt 2>&1
if errorlevel 1 set "FAILED=1"
>>test-results.txt echo OVERALL_FAILURE=%FAILED%
type test-results.txt
if "%FAILED%"=="0" (rmdir "%TESTDIR%" 2>nul) else (echo Failed tests may have kept fixtures in "%TESTDIR%".)
echo Results are saved in test-results.txt.
pause
exit /b %FAILED%
