# Vertical Video Factory

The orchestrated worker can now render queued content jobs into real local MP4 drafts for TikTok and YouTube Shorts review.

## Requirements

- Python 3.11+
- FFmpeg and ffprobe on PATH
- Ollama is optional but recommended for richer scripts
- Edge TTS is installed with the backend dependencies and is used for voiceover when online

## Install on Windows

From the repository root:

```powershell
cd backend
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Verify FFmpeg:

```powershell
ffmpeg -version
ffprobe -version
```

If FFmpeg is missing, install an FFmpeg build for Windows and add its `bin` directory to PATH before running the worker.

## Run one full cycle

```powershell
python run_agent_cycle.py --model qwen3:4b
```

The cycle performs maintenance, plans revenue-focused work, executes queued jobs and renders eligible jobs to MP4.

Output layout:

```text
backend/outputs/media/<job_id>/
├── video.mp4
├── voice.mp3          # when TTS succeeds
├── script.txt
├── scene-01.txt
├── scene-02.txt
└── manifest.json
```

Rendered video defaults:

- 1080 × 1920 portrait
- 30 fps
- H.264 video
- AAC audio when voiceover succeeds
- fast-start MP4
- maximum 90 seconds

The renderer uses Edge TTS for voiceover. If TTS is unavailable, it still creates a silent vertical MP4 so the job is not lost.

## Useful switches

Run without Ollama:

```powershell
python run_agent_cycle.py --no-ollama
```

Execute jobs but skip video rendering:

```powershell
python run_agent_cycle.py --no-video
```

Change the default TTS voice:

```powershell
$env:EDGE_TTS_VOICE="en-US-AriaNeural"
python run_agent_cycle.py
```

Change output directory:

```powershell
$env:MEDIA_OUTPUT_DIR="C:\Affiliate-AI\renders"
python run_agent_cycle.py
```

## Safety boundary

The video worker creates drafts only. It does not publish to TikTok or YouTube, spend money, create ads, or modify financial settings. A publishing connector should consume only human-approved MP4s from this output directory.
