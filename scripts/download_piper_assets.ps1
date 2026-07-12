$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$piperZip = Join-Path $projectRoot "tools/piper_windows_amd64.zip"
$piperDir = Join-Path $projectRoot "tools/piper"
$voicesDir = Join-Path $projectRoot "voices"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $piperZip), $piperDir, $voicesDir | Out-Null

Invoke-WebRequest `
  -Uri "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip" `
  -OutFile $piperZip

Expand-Archive -LiteralPath $piperZip -DestinationPath $piperDir -Force

Invoke-WebRequest `
  -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx" `
  -OutFile (Join-Path $voicesDir "en_US-lessac-medium.onnx")

Invoke-WebRequest `
  -Uri "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" `
  -OutFile (Join-Path $voicesDir "en_US-lessac-medium.onnx.json")

Write-Host "Piper and en_US-lessac-medium voice assets are ready."
