# Daily Polymarket scan (Windows Task Scheduler friendly)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  $py = "python"
}

& $py -m polymarket_agent.cli daily-scan --limit 50 --top 20
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py -m polymarket_agent.cli eval
exit $LASTEXITCODE
