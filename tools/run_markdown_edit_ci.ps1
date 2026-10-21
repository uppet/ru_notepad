# Experimental-only orchestration; never packages or certifies product acceptance.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$RuRoot,
      [Parameter(Mandatory=$true)][string]$MsysRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -cne 'Windows_NT' -or $PSVersionTable.PSVersion.Major -lt 7) { throw 'MI_EDIT_HOST_REJECTED=1' }
if ($env:GITHUB_EVENT_NAME -cne 'push' -or $env:GITHUB_REF -cne 'refs/heads/mi-perf-prototype' -or
    $env:GITHUB_REPOSITORY -cne 'uppet/ru_notepad') { throw 'MI_EDIT_TRIGGER_REJECTED=1' }
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
$Bin = Join-Path $MsysRoot 'mingw64/bin'
$env:PATH = "$Bin;$env:PATH"
$Python = Resolve-Application 'python'
$Git = Resolve-Application 'git'
$Ci = Join-Path $Root 'build/markdown-edit-experiment'
if (Test-Path -LiteralPath $Ci) { throw 'MI_EDIT_FRESH_DIRECTORY_REQUIRED=1' }
$Evidence = Join-Path $Ci 'private'
$Output = Join-Path $Ci 'bin'
$Measurements = Join-Path $Ci 'measurements'
New-Item -ItemType Directory -Path $Evidence,$Output,$Measurements -ErrorAction Stop | Out-Null
$script:Sequence = 0
function Invoke-Checked([string]$Command, [string[]]$Arguments) {
    $script:Sequence++
    $Log = Join-Path $Evidence ('command-{0:D3}.log' -f $script:Sequence)
    & $Command @Arguments *> $Log
    $Code = $LASTEXITCODE
    if ($Arguments.Count -ge 1 -and $Arguments[0] -ceq (Join-Path $PSScriptRoot 'run_markdown_edit_controls.py')) {
        foreach ($Line in Get-Content -LiteralPath $Log) {
            if ($Line -cmatch '^MI_EDIT_CONTROL module=[1-7] case=[0-9]{1,4} status=[12] line=[0-9]{1,5} exception=[1-3]$' -or
                $Line -cmatch '^MI_EDIT_CONTROL module=[1-7] cases=[0-9]{1,4} failed=[0-9]{1,4} errors=[0-9]{1,4} skipped=[0-9]{1,4}$') { Write-Host $Line }
        }
    }
    if ($Code -ne 0) { throw ('MI_EDIT_COMMAND_FAILED=' + $script:Sequence) }
    Write-Host ('MI_EDIT_COMMAND_COMPLETE=' + $script:Sequence)
}
Push-Location $Root
try {
    $Head = (& $Git -C $RuRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $Head -cne '85c7821fda35aa79deeaf67b4d430f24ddd7f07f') { throw 'MI_EDIT_COMPILER_REJECTED=1' }
    $Tree = (& $Git -C $RuRoot rev-parse 'HEAD^{tree}').Trim()
    if ($LASTEXITCODE -ne 0 -or $Tree -cne 'a770e367e84d87a0d2fcb6d49ea6f06da2dbe4ba') { throw 'MI_EDIT_TREE_REJECTED=1' }
    $Dirty = & $Git -C $RuRoot status --porcelain
    if ($LASTEXITCODE -ne 0 -or $Dirty) { throw 'MI_EDIT_DIRTY_COMPILER=1' }
    foreach ($Name in @('test_markdown_edit_ci.py','test_markdown_control_markers.py','test_markdown_owned_workflow.py',
            'test_markdown_edit_transform.py','test_markdown_edit_profile.py',
            'test_markdown_edit_late.py','test_markdown_edit_observers.py')) {
        Invoke-Checked $Python @((Join-Path $PSScriptRoot 'run_markdown_edit_controls.py'),'--module',($Name -replace '\.py$',''))
    }
    Invoke-Checked $Python @((Join-Path $PSScriptRoot 'test_markdown_owned_profile.py'),'--cc',(Join-Path $Bin 'gcc.exe'))
    Invoke-Checked $Python @((Join-Path $PSScriptRoot 'test_markdown_edit_windows.py'),'--cc',(Join-Path $Bin 'gcc.exe'),'--objdump',(Join-Path $Bin 'objdump.exe'))
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
    $DiagnosticLexillaArgs = @()
    $DiagnosticLexillaArgs = @('windir=C:/Windows')
    Invoke-Checked (Join-Path $Bin 'mingw32-make.exe') (@(
        '-j2','-C',(Join-Path $Root 'vendor/lexilla/src'),'../bin/lexilla.dll',
        'CXX=g++.exe','WINDRES=windres.exe','AR=ar.exe','RANLIB=ranlib.exe',
        'LDFLAGS=-shared -static -mwindows -Wl,--kill-at -s'
    ) + $DiagnosticLexillaArgs)
    Invoke-Checked $Python @('tools/check_static.py','--ru-root',$RuRoot)
    $BuildArgs = @('tools/build.py','--ru-root',$RuRoot,
        '--cc',(Join-Path $Bin 'gcc.exe'),'--cxx',(Join-Path $Bin 'g++.exe'),
        '--windres',(Join-Path $Bin 'windres.exe'),'--ar',(Join-Path $Bin 'ar.exe'),
        '--ranlib',(Join-Path $Bin 'ranlib.exe'),'--skip-scintilla','--skip-lexilla')
    Invoke-Checked $Python ($BuildArgs + @('--source','src/main.ru','--output',(Join-Path $Output 'ru_notepad.exe')))

    # CLI publishes only a validated, bounded numeric/hash JSON, including failure.
    # A late diagnostic still exits nonzero: the 30-second product gate is intact.
    & $Python (Join-Path $PSScriptRoot 'run_markdown_edit_profile.py') `
        --ru-root $RuRoot --binary-dir $Output --evidence-dir $Measurements `
        --cc (Join-Path $Bin 'gcc.exe') --windres (Join-Path $Bin 'windres.exe')
    if ($LASTEXITCODE -ne 0) { throw 'MI_EDIT_DIAGNOSTIC_OR_PRODUCT_GATE_FAILED=1' }
} finally { Pop-Location }
