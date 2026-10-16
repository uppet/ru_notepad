# Real Windows/NTFS tests. Run only in a disposable, trusted local test directory.
# Creates synthetic fixtures only. Requires the separately built pure-Ru probe.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProbeExe,
    [Parameter(Mandatory=$true)][string]$TestDirectory
)
$ErrorActionPreference = 'Stop'
$ProbeExe = (Resolve-Path -LiteralPath $ProbeExe).Path
$TestDirectory = (Resolve-Path -LiteralPath $TestDirectory).Path
if ($env:OS -ne 'Windows_NT') { throw 'Real Windows is required for this ACL test.' }
$root = Join-Path $TestDirectory ('ru-codec-acl-test-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$worldSid = [Security.Principal.SecurityIdentifier]::new('S-1-1-0')
$inherit = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
$allow = [Security.AccessControl.AccessControlType]::Allow
$none = [Security.AccessControl.PropagationFlags]::None
$utf8 = [Text.UTF8Encoding]::new($false)

function Assert-True([bool]$condition, [string]$message) {
    if (-not $condition) { throw $message }
    Write-Host ('PASS: ' + $message)
}
function Access-RuleTuples([string]$path) {
    # Sorted ACE tuples for these allow-only fixtures, not an effective-access evaluator.
    # Ignores inherited provenance and ACE order; owner/conditional ACEs are not tested.
    $acl = Get-Acl -LiteralPath $path
    @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]) |
        ForEach-Object {
            '{0}|{1}|{2}|{3}|{4}' -f $_.IdentityReference.Value,
                $_.AccessControlType, [int]$_.FileSystemRights,
                [int]$_.InheritanceFlags, [int]$_.PropagationFlags
        } | Sort-Object) -join "`n"
}
try {
    # A permissive parent proves that the staging descriptor blocks new inheritance.
    # Only this newly created synthetic-test directory receives this ACL.
    $directoryAcl = [Security.AccessControl.DirectorySecurity]::new()
    $directoryAcl.SetAccessRuleProtection($true, $false)
    $directoryAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        $worldSid, [Security.AccessControl.FileSystemRights]::FullControl,
        $inherit, $none, $allow))
    Set-Acl -LiteralPath $root -AclObject $directoryAcl

    foreach ($protected in @($true, $false)) {
        $label = if ($protected) { 'protected' } else { 'inherited' }
        $target = Join-Path $root ($label + '.txt')
        [IO.File]::WriteAllText($target, "synthetic original`r`n", $utf8)
        if ($protected) {
            $fileAcl = [Security.AccessControl.FileSecurity]::new()
            $fileAcl.SetAccessRuleProtection($true, $false)
            $fileAcl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                $currentSid, [Security.AccessControl.FileSystemRights]::FullControl, $allow))
            Set-Acl -LiteralPath $target -AclObject $fileAcl
        }
        $beforeRules = Access-RuleTuples $target
        $beforeProtected = (Get-Acl -LiteralPath $target).AreAccessRulesProtected
        Assert-True ($beforeProtected -eq $protected) "$label source ACL fixture"
        & $ProbeExe $target save
        Assert-True ($LASTEXITCODE -eq 0) "$label ordinary replacement"
        Assert-True (([IO.File]::ReadAllText($target)) -eq "synthetic replacement`r`n") "$label saved bytes"
        Assert-True ((Access-RuleTuples $target) -ceq $beforeRules) "$label final allow-only ACE tuples preserved"
        Assert-True ((Get-Acl -LiteralPath $target).AreAccessRulesProtected -eq $beforeProtected) "$label final protection flag preserved"

        # Keep a read handle which disallows deletion. Reading/staging succeeds,
        # but ReplaceFileW must fail and expose the retained staging files.
        [IO.File]::WriteAllText($target, "synthetic original`r`n", $utf8)
        $beforeRules = Access-RuleTuples $target
        $guard = [IO.File]::Open($target, [IO.FileMode]::Open,
            [IO.FileAccess]::Read, [IO.FileShare]::Read)
        try {
            & $ProbeExe $target expect-replace-failure
            Assert-True ($LASTEXITCODE -eq 0) "$label forced replacement failure"
        } finally { $guard.Dispose() }
        Assert-True (([IO.File]::ReadAllText($target)) -eq "synthetic original`r`n") "$label original survived sharing failure"
        $staging = @(Get-ChildItem -LiteralPath $root -File |
            Where-Object { $_.Name.StartsWith($label + '.txt.ru-notepad-') -and $_.Name.EndsWith('.tmp') })
        Assert-True ($staging.Count -eq 1) "$label retained staged document"
        $stage = $staging[0].FullName
        Assert-True (([IO.File]::ReadAllText($stage)) -eq "synthetic replacement`r`n") "$label staged bytes retained"
        Assert-True ((Get-Acl -LiteralPath $stage).AreAccessRulesProtected) "$label staging blocks directory inheritance"
        Assert-True ((Access-RuleTuples $stage) -ceq $beforeRules) "$label staging allow-only ACE tuples preserved"
        $backups = @(Get-ChildItem -LiteralPath $root -File |
            Where-Object { $_.Name.StartsWith($label + '.txt.ru-notepad-') -and $_.Name.EndsWith('.bak') })
        Assert-True ($backups.Count -eq 1) "$label reserved backup retained"
        Assert-True ((Get-Acl -LiteralPath $backups[0].FullName).AreAccessRulesProtected) "$label backup blocks directory inheritance"
        Assert-True ((Access-RuleTuples $backups[0].FullName) -ceq $beforeRules) "$label backup allow-only ACE tuples preserved"
    }
    Write-Host 'FILE_CODEC_SECURITY_TESTS_PASS'
} finally {
    # Only the uniquely created synthetic fixture directory is removed.
    Remove-Item -LiteralPath $root -Recurse -Force
}
