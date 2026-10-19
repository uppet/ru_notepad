# Reproducible source pins; actual MinGW package versions are recorded per run.
# Run in a clean disposable Windows checkout. No user documents are opened.
# Requires PowerShell 7, Python 3.12+, Git, and official MSYS2 MinGW64 packages.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RuRoot,
    [string]$ResearchBaselineRoot,
    [Parameter(Mandatory=$true)][string]$MsysRoot,
    [switch]$RunAclTests,
    [switch]$RunCallbackResearch
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

# Validate ordinary download bytes before any archive extraction or build.
function Expand-VerifiedArchive(
    [string]$Archive, [string]$DestinationPath,
    [long]$ExpectedSize, [string]$ExpectedSha256
) {
    if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) {
        throw 'Official archive is missing; refusing extraction or execution.'
    }
    if ((Get-Item -LiteralPath $Archive).Length -ne $ExpectedSize) {
        throw 'Official archive size mismatch; refusing extraction or execution.'
    }
    $Stream = [System.IO.File]::OpenRead($Archive)
    try {
        $Magic = [byte[]]::new(4)
        if ($Stream.Read($Magic, 0, 4) -ne 4 -or
            $Magic[0] -ne 0x50 -or $Magic[1] -ne 0x4b -or
            $Magic[2] -ne 0x03 -or $Magic[3] -ne 0x04) {
            throw 'Official archive ZIP magic mismatch; refusing extraction or execution.'
        }
    } finally {
        $Stream.Dispose()
    }
    if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256) {
        throw 'Official archive SHA256 mismatch; refusing extraction or execution.'
    }
    $Zip = $null
    try {
        $Zip = [System.IO.Compression.ZipFile]::OpenRead($Archive)
        if ($Zip.Entries.Count -eq 0) { throw 'Empty archive' }
    } catch {
        throw 'Official archive is a malformed ZIP; refusing extraction or execution.'
    } finally {
        if ($null -ne $Zip) { $Zip.Dispose() }
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $DestinationPath
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

# Research is separate from product acceptance. Even an unsuccessful research
# sample must not prevent the original full product inventory from executing.
function Invoke-ResearchThenAcceptance(
    [string]$Command, [string[]]$ResearchArguments, [string[]]$AcceptanceArguments,
    [bool]$ControlsPassed = $true
) {
    $ResearchPassed = $false
    if ($ControlsPassed) {
        try {
            Invoke-Checked $Command $ResearchArguments
            $ResearchPassed = $true
        } catch {
            Write-Host 'MARKDOWN_CALLBACK_RESEARCH_FAILED=1'
        }
    } else {
        Write-Host 'MARKDOWN_CALLBACK_RESEARCH_CONTROLS_FAILED=1'
    }
    Invoke-Checked $Command $AcceptanceArguments
    if (-not $ResearchPassed) {
        throw 'Markdown callback research failed; full product execution was still attempted.'
    }
}
# Optional measurements cannot mask product failure or turn product success into
# failure. Every public fallback is fixed metadata, never exception text.
function Invoke-OptionalMarkdownStudy(
    [string]$Python, [string[]]$ControlArguments, [string[]]$RunArguments,
    [string]$Evidence,
    [ValidateSet('native-baseline','cpu-profile')][string]$Name
) {
    $SavedExit = $global:LASTEXITCODE
    $Stage = 'host_controls'
    try {
        Invoke-Checked $Python $ControlArguments
        $Stage = 'execution'
        Invoke-Checked $Python $RunArguments
    } catch {
        Write-Host ('MARKDOWN_OPTIONAL_STUDY_FAILED=' + $Name)
        try {
            @{ schema = 1; diagnostic_only = $true; status = 'unavailable';
                stage = $Stage; reason = 'optional_study_command_failed';
                measurement_claimed = $false } | ConvertTo-Json -Depth 3 |
                Set-Content -LiteralPath (Join-Path $Evidence ("markdown-" + $Name + "-runner-failure.json")) -Encoding utf8
        } catch {
            Write-Host 'MARKDOWN_OPTIONAL_STUDY_EVIDENCE_UNAVAILABLE=1'
        }
    } finally {
        $global:LASTEXITCODE = $SavedExit
    }
}
function Git-Value([string[]]$Arguments) {
    $value = & $Git -C $RuRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the pinned Ru checkout.' }
    return ($value -join "`n").Trim()
}

Push-Location $Root
try {
    if ((Git-Value @('rev-parse','HEAD')) -ne '85c7821fda35aa79deeaf67b4d430f24ddd7f07f') {
        throw 'Ru public commit does not match the reviewed pin.'
    }
    if ((Git-Value @('rev-parse','HEAD^{tree}')) -ne 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba') {
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
    Invoke-Checked $Python @('-I','tools/test_ru_cli_diagnostics.py','--ru-root',$RuRoot,'-v')
    # Historical research is opt-in. Normal product CI does not execute a
    # locked old-source experiment against a new application graph.
    if ($RunCallbackResearch) {
        # A research-only control failure prohibits research execution, but it
        # does not suppress the independent original product builds/acceptance.
        $ResearchControlsPassed = $false
        try {
            Invoke-Checked $Python @('tools/test_markdown_callback_cost.py')
            $ResearchControlsPassed = $true
        } catch {
            Write-Host 'MARKDOWN_CALLBACK_RESEARCH_CONTROLS_FAILED=1'
            $ControlFailure = @{
                schema = 2; research_only = $true; product_acceptance = 'not_claimed'
                status = 'failed'; samples = @()
                failure = @{ stage = 'host_controls'; code = 'research_controls_failed' }
            }
            $ControlFailure | ConvertTo-Json -Depth 4 |
                Set-Content -LiteralPath (Join-Path $Evidence 'markdown-callback-summary.json') -Encoding utf8
        }
    }
    Invoke-Checked $Python @('tools/test_markdown_portable.py','--ru-root',$RuRoot,
        '--cc',(Join-Path $Bin 'gcc.exe'))

    # Run the complete helper suite on this host before admitting source bytes.
    # The helper copies only reviewed in-repository ZIPs and never extracts.
    Invoke-Checked $Python @('tools/test_source_archives.py')
    Invoke-Checked $Python @('tools/prepare_source_archives.py','--root',$Root,
        '--receipt',(Join-Path $Evidence 'source-archives.json'))
    $Downloads = Join-Path $Root 'vendor/downloads'
    $Archive = Join-Path $Downloads 'scintilla567.zip'
    if (Test-Path -LiteralPath (Join-Path $Root 'vendor/scintilla')) {
        throw 'Use a fresh checkout: vendor/scintilla already exists.'
    }
    Expand-VerifiedArchive -Archive $Archive -DestinationPath (Join-Path $Root 'vendor') `
        -ExpectedSize 1904249 -ExpectedSha256 '2309181e59e7da4659f890dbc128db7451ccd094748770e7be674b830494587c'
    $LexillaArchive = Join-Path $Downloads 'lexilla554.zip'
    if (Test-Path -LiteralPath (Join-Path $Root 'vendor/lexilla')) {
        throw 'Use a fresh checkout: vendor/lexilla already exists.'
    }
    Expand-VerifiedArchive -Archive $LexillaArchive -DestinationPath (Join-Path $Root 'vendor') `
        -ExpectedSize 1598324 -ExpectedSha256 '5e0a21356e4e2f19d6a38ecd1c8172d5a2b7b4542940568b023386080db90fe0'
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
    # The bounded fold helper is a product input, unlike optional timing studies.
    # Execute shared-core controls and the real DLL/foreign-owner tests before
    # admitting any product native/GUI result; these are mandatory on Windows.
    Invoke-Checked $Python @('-I','tools/test_markdown_fold_helper.py',
        '--cc',(Join-Path $Bin 'gcc.exe'),'--runtime-dir',$Output,
        '--output',(Join-Path $Evidence 'markdown-bulk-helper-controls.json'))
    foreach ($test in @('document_policy','ui_arguments','file_codec_flags','editor_native','app_native','app_features_native','file_codec_tests','file_codec_security_probe','syntax_native','syntax_policy','shortcuts','status_native','file_streaming_native','editor_streaming_native','associations_policy','associations_native','file_drop_native','app_streaming_native','ru_lexical_policy','ru_syntax_native','app_ru_native','ru_direct_styling_native','markdown_policy','markdown_selection_policy','markdown_native','app_markdown_native','markdown_direct_native')) {
        Invoke-Checked $Python ($BuildArgs + @('--console','--source',"tests/$test.ru",'--output',(Join-Path $Output "$test.exe")))
    }
    $AcceptArgs = @('tools/windows_ci.py','--bin-dir',$Output,'--evidence-dir',$Evidence,
        '--mingw-root',$MinGW,'--objdump',(Join-Path $Bin 'objdump.exe'))
    if ($RunAclTests) { $AcceptArgs += '--acl' }
    if ($RunCallbackResearch) {
        # The research EXE and its instrumented translation unit stay outside bin
        # and the package inventory. Each compiler uses one binary for both modes.
        # The candidate compiler must also match the accepted product pin. Both
        # accepted pins and exact generated-C comparison are required before launch.
        if ([string]::IsNullOrWhiteSpace($ResearchBaselineRoot)) {
            $ResearchBaselineRoot = Join-Path $Root '.ci/ru-research-baseline'
        }
        $ResearchArgs = @('tools/run_markdown_callback_cost.py','--ru-root',$RuRoot,
            '--old-ru-root',$ResearchBaselineRoot,'--new-ru-root',$RuRoot,
            '--binary-dir',$Output,'--evidence-dir',$Evidence,
            '--cc',(Join-Path $Bin 'gcc.exe'),'--windres',(Join-Path $Bin 'windres.exe'))
        Invoke-ResearchThenAcceptance $Python $ResearchArgs $AcceptArgs -ControlsPassed $ResearchControlsPassed
    } else {
        try {
            Invoke-Checked $Python $AcceptArgs
        } finally {
            # Diagnostics are separate runs AFTER the original acceptance. Their
            # commands/JSON failures cannot replace its exception or exit status.
            $ProductExit = $global:LASTEXITCODE
            try {
                Invoke-OptionalMarkdownStudy $Python @('tools/test_markdown_native_baseline.py','-v') @(
                    'tools/run_markdown_native_baseline.py','--cc',(Join-Path $Bin 'gcc.exe'),
                    '--runtime-dir',$Output,'--output',(Join-Path $Evidence 'markdown-native-baseline.json')
                ) $Evidence 'native-baseline'
                Invoke-OptionalMarkdownStudy $Python @('tools/test_markdown_cpu_profile.py','-v') @(
                    'tools/run_markdown_cpu_profile.py','--runtime-dir',$Output,
                    '--output',(Join-Path $Evidence 'markdown-cpu-profile.json')
                ) $Evidence 'cpu-profile'
            } catch {
                Write-Host 'MARKDOWN_OPTIONAL_DIAGNOSTICS_UNAVAILABLE=1'
            } finally {
                $global:LASTEXITCODE = $ProductExit
            }
        }
    }
} finally {
    Pop-Location
}
