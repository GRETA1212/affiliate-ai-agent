$ErrorActionPreference = "Stop"

Write-Host "== Affiliate Video Factory setup =="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git is required and was not found on PATH."
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Host "Installing FFmpeg..."
  winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
  throw "FFmpeg was installed. Reopen PowerShell so PATH refreshes, then run this script again."
}

$py310 = $null
try {
  $candidate = py -3.10 -c "import sys; print(sys.executable)" 2>$null
  if ($LASTEXITCODE -eq 0) { $py310 = $candidate.Trim() }
} catch {}

if (-not $py310) {
  Write-Host "Python 3.10 is missing. Installing it..."
  winget install --id Python.Python.3.10 -e --accept-package-agreements --accept-source-agreements
  throw "Python 3.10 was installed. Reopen PowerShell, then run this script again."
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
    & $py310 -m venv .venv
  }
  $python = Resolve-Path ".venv/Scripts/python.exe"
  & $python -m pip install --upgrade pip

  # Official MuseTalk baseline for Windows/CUDA-compatible NVIDIA systems.
  & $python -m pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
  & $python -m pip install -r requirements.txt
  & $python -m pip install --no-cache-dir -U openmim
  & $python -m mim install mmengine
  & $python -m mim install "mmcv==2.0.1"
  & $python -m mim install "mmdet==3.1.0"
  & $python -m mim install "mmpose==1.1.0"

  if (Test-Path "download_weights.bat") {
    cmd /c download_weights.bat
  } else {
    Write-Warning "download_weights.bat was not found. Download MuseTalk 1.5 weights into vendor/MuseTalk/models."
  }

  & $python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
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
