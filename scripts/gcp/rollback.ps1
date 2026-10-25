# PowerShell 5.1+ entry point; orchestration and validation use Python stdlib.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('dev','prod')][string]$Environment,
    [string]$ImageTag,
    [string]$ConfigDir,
    [switch]$DryRun,
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PythonPath = Join-Path $RepositoryRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $PythonPath)) {
    $PythonCommand = Get-Command python -ErrorAction Stop
    $PythonPath = $PythonCommand.Source
}
$Arguments = @((Join-Path $PSScriptRoot 'deployment.py'), 'rollback', '--environment', $Environment)
if ($ImageTag) { $Arguments += @('--image-tag', $ImageTag) }
if ($ConfigDir) { $Arguments += @('--config-dir', $ConfigDir) }
if ($DryRun) { $Arguments += '--dry-run' }
if ($Offline) { $Arguments += '--offline' }
& $PythonPath @Arguments
exit $LASTEXITCODE
