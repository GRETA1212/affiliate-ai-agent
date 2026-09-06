$ErrorActionPreference = "Stop"

Write-Host "== Affiliate Video Factory setup =="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git is required and was not found on PATH."
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python is required and was not found on PATH."
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "FFmpeg is missing. Install it with: winget install --id Gyan.FFmpeg -e"
  throw "Install FFmpeg, reopen PowerShell, and run this script again."
}

New-Item -ItemType Directory -Force -Path vendor | Out-Null
if (-not (Test-Path "vendor/MuseTalk/.git")) {
  git clone https://github.com/TMElyralab/MuseTalk.git vendor/MuseTalk
} else {
  Write-Host "MuseTalk checkout already exists."
}

Push-Location vendor/MuseTalk
try {
  if (-not (Test-Path ".venv/Scripts/python.exe")) {
    python -m venv .venv
  }
  & .\.venv\Scripts\python.exe -m pip install --upgrade pip
  & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  & .\.venv\Scripts\python.exe -m pip install --no-cache-dir -U openmim
  & .\.venv\Scripts\python.exe -m mim install mmengine
  & .\.venv\Scripts\python.exe -m mim install "mmcv==2.0.1"
  & .\.venv\Scripts\python.exe -m mim install "mmdet==3.1.0"
  & .\.venv\Scripts\python.exe -m mim install "mmpose==1.1.0"

  if (Test-Path "download_weights.bat") {
    cmd /c download_weights.bat
  } else {
    Write-Warning "download_weights.bat was not found. Follow MuseTalk's model-download instructions."
  }
} finally {
  Pop-Location
}

New-Item -ItemType Directory -Force -Path assets/avatar, assets/audio, output/videos | Out-Null

Write-Host ""
Write-Host "Setup stage finished."
Write-Host "Put presenter image at assets/avatar/maya.png"
Write-Host "Put narration WAV at assets/audio/taskade-video-01.wav"
Write-Host "Then run: affiliate-intel video-plan data/video_jobs/taskade-video-01.json"
Write-Host "When ready: affiliate-intel video-render data/video_jobs/taskade-video-01.json --musetalk-root vendor/MuseTalk"
