# Load the repo-root .env into the CURRENT PowerShell session as environment
# variables, so dbt (and any tool using env_var) can read the warehouse creds.
#
# Dot-source it so the variables persist in your session:
#   . .\scripts\load-env.ps1
$envPath = Join-Path $PSScriptRoot '..\.env'
if (-not (Test-Path $envPath)) {
    Write-Error ".env not found at $envPath  (copy .env.example to .env first)"
    return
}
Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq '' -or $line.StartsWith('#')) { return }
    $idx = $line.IndexOf('=')
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim()
    # Strip a single pair of surrounding single or double quotes, if present.
    if ($val.Length -ge 2 -and
        (($val[0] -eq "'" -and $val[$val.Length - 1] -eq "'") -or
         ($val[0] -eq '"' -and $val[$val.Length - 1] -eq '"'))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    Set-Item -Path ("env:" + $key) -Value $val
}
Write-Host "Loaded warehouse env vars from .env into this session."
