$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

if (Test-Path ".venv\Scripts\Activate.ps1") {
  . ".venv\Scripts\Activate.ps1"
}

Write-Host "==> Installing backend requirements"
python -m pip install -r "backend\requirements.txt"

Write-Host "==> Installing Playwright"
python -m pip install playwright requests
python -m playwright install chromium

New-Item -ItemType Directory -Force -Path ".logs" | Out-Null

Write-Host "==> Starting BentoML service on :3000"
$bentoOut = Join-Path ".logs" "bentoml.out.log"
$bentoErr = Join-Path ".logs" "bentoml.err.log"
$bentoProc = Start-Process -FilePath "bentoml" `
  -ArgumentList @("serve","backend.main:svc","--host","0.0.0.0","--port","3000") `
  -RedirectStandardOutput $bentoOut `
  -RedirectStandardError $bentoErr `
  -PassThru

function Stop-Bento {
  if ($null -ne $bentoProc -and -not $bentoProc.HasExited) {
    try { Stop-Process -Id $bentoProc.Id -Force } catch {}
  }
}

try {
  Write-Host "==> Waiting for backend to accept connections"
  $deadline = (Get-Date).AddSeconds(60)
  while ((Get-Date) -lt $deadline) {
    $client = $null
    try {
      $client = New-Object System.Net.Sockets.TcpClient
      $async = $client.BeginConnect("127.0.0.1", 3000, $null, $null)
      if ($async.AsyncWaitHandle.WaitOne(500)) {
        $client.EndConnect($async)
        Write-Host "Backend is up."
        break
      }
    } catch {
      Start-Sleep -Milliseconds 500
    } finally {
      if ($client) { $client.Close() }
    }
  }

  if ((Get-Date) -ge $deadline) {
    throw "Timed out waiting for backend on :3000. See .logs\bentoml.*.log for details."
  }

  Write-Host "==> Running browser agent"
  python "browser-agent\main.py"
}
finally {
  Stop-Bento
}

