# Reproducible source pins; actual MinGW package versions are recorded per run.
# Run in a clean disposable Windows checkout. No user documents are opened.
# Requires PowerShell 7, Python 3.12+, Git, and official MSYS2 MinGW64 packages.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RuRoot,
    [Parameter(Mandatory=$true)][string]$MsysRoot,
    [switch]$RunAclTests
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This acceptance run requires real Windows.' }
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 or newer is required.' }
# Get-Command can return every matching PATH application, even without -All.
# Resolve one executable object before reading Source; never flatten path arrays.
function Resolve-Application([string]$Name) {
    $Command = Get-Command -Name $Name -CommandType Application -ErrorAction Stop |
        Select-Object -First 1
    if ($null -eq $Command -or [string]::IsNullOrWhiteSpace($Command.Source) -or
        -not (Test-Path -LiteralPath $Command.Source -PathType Leaf)) {
        throw "No usable application path for: $Name"
    }
    return [string]$Command.Source
}

$Root = Split-Path -Parent $PSScriptRoot
$RuRoot = (Resolve-Path -LiteralPath $RuRoot).Path
$MsysRoot = (Resolve-Path -LiteralPath $MsysRoot).Path
$MinGW = Join-Path $MsysRoot 'mingw64'
$Bin = Join-Path $MinGW 'bin'
$Python = Resolve-Application 'python'
$Git = Resolve-Application 'git'
$env:PATH = "$Bin;$env:PATH"
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    Write-Host ('> ' + $Command + ' ' + ($Arguments -join ' '))
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code ${LASTEXITCODE}: $Command" }
}
function Git-Value([string[]]$Arguments) {
    $value = & $Git -C $RuRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the pinned Ru checkout.' }
    return ($value -join "`n").Trim()
}

Push-Location $Root
try {
    if ((Git-Value @('rev-parse','HEAD')) -ne 'a2f6faa0f914781dea74cb6f0a7574f1dd6808ce') {
        throw 'Ru public commit does not match the reviewed pin.'
    }
    if ((Git-Value @('rev-parse','HEAD^{tree}')) -ne '7b4331d51bc6ab2ec95fec1f8368465343fcd5af') {
        throw 'Ru compiler tree does not match the reviewed pin.'
    }
    if (Git-Value @('status','--porcelain')) { throw 'Ru checkout must be unmodified.' }
    foreach ($name in @('gcc.exe','g++.exe','windres.exe','ar.exe','ranlib.exe','objdump.exe','mingw32-make.exe')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Bin $name) -PathType Leaf)) { throw "Missing official MinGW tool: $name" }
    }
    $Ci = Join-Path $Root 'build/windows-ci'
    if (Test-Path -LiteralPath $Ci) { throw 'Use a fresh checkout: build/windows-ci already exists.' }
    $Evidence = Join-Path $Ci 'evidence'
    $Output = Join-Path $Ci 'bin'
    New-Item -ItemType Directory -Path $Evidence,$Output -Force | Out-Null
    $packages = & (Join-Path $MsysRoot 'usr/bin/pacman.exe') -Q
    if ($LASTEXITCODE -ne 0) { throw 'Could not record installed MSYS2 package versions.' }
    $packages | Set-Content -LiteralPath (Join-Path $Evidence 'msys2-packages.log') -Encoding utf8
    Invoke-Checked (Join-Path $Bin 'gcc.exe') @('--version')
    Invoke-Checked $Python @('--version')
    # Orchestration tests are separate from the native application acceptance.
    Invoke-Checked $Python @('tools/test_windows_ci.py')
    Invoke-Checked $Python @('tools/test_package.py')

    $Downloads = Join-Path $Root 'vendor/downloads'
    New-Item -ItemType Directory -Path $Downloads -Force | Out-Null
    $Archive = Join-Path $Downloads 'scintilla567.zip'
    Invoke-WebRequest -Uri 'https://www.scintilla.org/scintilla567.zip' -OutFile $Archive -TimeoutSec 120
    if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c') {
        throw 'Official Scintilla archive hash mismatch; refusing extraction or execution.'
    }
    if (Test-Path -LiteralPath (Join-Path $Root 'vendor/scintilla')) {
        throw 'Use a fresh checkout: vendor/scintilla already exists.'
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath (Join-Path $Root 'vendor')
    $LexillaArchive = Join-Path $Downloads 'lexilla554.zip'
    Invoke-WebRequest -Uri 'https://www.scintilla.org/lexilla554.zip' -OutFile $LexillaArchive -TimeoutSec 120
    if ((Get-FileHash -LiteralPath $LexillaArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0') {
        throw 'Official Lexilla archive hash mismatch; refusing extraction or execution.'
    }
    if (Test-Path -LiteralPath (Join-Path $Root 'vendor/lexilla')) {
        throw 'Use a fresh checkout: vendor/lexilla already exists.'
    }
    Expand-Archive -LiteralPath $LexillaArchive -DestinationPath (Join-Path $Root 'vendor')
    # Native MinGW make uses the official Windows makefile and static C++ runtime.
    Invoke-Checked (Join-Path $Bin 'mingw32-make.exe') @(
        '-j2','-C',(Join-Path $Root 'vendor/scintilla/win32'),'../bin/Scintilla.dll',
        'CXX=g++.exe','WINDRES=windres.exe','AR=ar.exe','RANLIB=ranlib.exe'
    )
    Invoke-Checked (Join-Path $Bin 'mingw32-make.exe') @(
        '-j2','-C',(Join-Path $Root 'vendor/lexilla/src'),'../bin/lexilla.dll',
        'CXX=g++.exe','WINDRES=windres.exe','AR=ar.exe','RANLIB=ranlib.exe',
        'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'
    )
    Invoke-Checked $Python @('tools/check_static.py','--ru-root',$RuRoot)
    $BuildArgs = @('tools/build.py','--ru-root',$RuRoot,
        '--cc',(Join-Path $Bin 'gcc.exe'),'--cxx',(Join-Path $Bin 'g++.exe'),
        '--windres',(Join-Path $Bin 'windres.exe'),'--ar',(Join-Path $Bin 'ar.exe'),
        '--ranlib',(Join-Path $Bin 'ranlib.exe'),'--skip-scintilla','--skip-lexilla')
    Invoke-Checked $Python ($BuildArgs + @('--source','src/main.ru','--output',(Join-Path $Output 'ru_notepad.exe')))
    foreach ($test in @('document_policy','ui_arguments','file_codec_flags','editor_native','app_native','app_features_native','file_codec_tests','file_codec_security_probe','syntax_native','syntax_policy','shortcuts','status_native','file_streaming_native','editor_streaming_native','associations_policy','associations_native','file_drop_native','app_streaming_native','ru_lexical_policy','ru_syntax_native','app_ru_native')) {
        Invoke-Checked $Python ($BuildArgs + @('--console','--source',"tests/$test.ru",'--output',(Join-Path $Output "$test.exe")))
    }
    $AcceptArgs = @('tools/windows_ci.py','--bin-dir',$Output,'--evidence-dir',$Evidence,
        '--mingw-root',$MinGW,'--objdump',(Join-Path $Bin 'objdump.exe'))
    if ($RunAclTests) { $AcceptArgs += '--acl' }
    Invoke-Checked $Python $AcceptArgs
} finally {
    Pop-Location
}
