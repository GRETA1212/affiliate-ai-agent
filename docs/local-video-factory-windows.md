# Local Video Factory — Windows

This pipeline is designed to avoid per-render avatar-platform limits for high-volume affiliate shorts.

## What the repo does now

The command below validates the local inputs and tools, then prints the exact render plan:

```powershell
affiliate-intel video-plan data/video_jobs/taskade-video-01.json
```

The first Taskade job expects:

- `assets/avatar/maya.png` — presenter portrait
- `assets/audio/taskade-video-01.wav` — narration audio
- `vendor/MuseTalk/scripts/inference.py` — local MuseTalk checkout
- `ffmpeg` on PATH

It outputs a planned vertical render at `outputs/taskade-video-01.mp4`.

## Recommended local folders

```text
assets/
  avatar/
    maya.png
  audio/
    taskade-video-01.wav
outputs/
vendor/
  MuseTalk/
```

Keep generated media and model weights out of Git. Do not commit private voice samples, raw selfies, model weights, or large rendered videos.

## Setup order

1. Install Git and FFmpeg and make sure `git --version` and `ffmpeg -version` work in PowerShell.
2. Create a dedicated Python environment for the video stack. Keep it separate from the lightweight affiliate API environment because GPU media dependencies are much heavier.
3. Clone MuseTalk under `vendor/MuseTalk` and follow its current upstream installation instructions for the NVIDIA/CUDA/PyTorch combination installed on the machine.
4. Put one approved presenter portrait at `assets/avatar/maya.png`.
5. Create narration audio and save it at `assets/audio/taskade-video-01.wav`.
6. Run the `video-plan` command. It should report `ready: true` only when the required local pieces exist.
7. Execute the emitted MuseTalk command to create the talking-head intermediate.
8. Execute the emitted FFmpeg command to compose the 9:16 affiliate-ready MP4 with disclosure text.

## Why planning is separate from rendering

The affiliate engine should be able to create campaign jobs without requiring GPU libraries on the production API server. Rendering stays local and can later be moved behind a worker without changing campaign data or analytics.

## Next implementation slice

Add `video-render` after the real MuseTalk command is verified on the target Windows machine. That command should execute the plan step-by-step, capture logs, fail safely, and register the produced content asset back into the affiliate database.
