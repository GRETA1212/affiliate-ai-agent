#!/usr/bin/env python3
"""
Fallback renderer.

Consumes the same RenderInput JSON as the Remotion composition and produces a
1080x1920 H.264 MP4 with a silent audio bed.

Why this exists: Remotion renders through headless Chromium, which has to be
downloaded. In an offline or network-restricted environment (CI, this sandbox,
a locked-down build agent) that download fails and the vertical slice would
stop at "storyboard" with nothing to look at. This renderer keeps the pipeline
end-to-end everywhere, using only Pillow and ffmpeg.

It is deliberately a *proof*, not a replacement: Remotion remains the real
renderer. The layout constants below mirror VerticalVideo.tsx so review frames
match what Remotion will output.
"""

import json
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
SAFE_TOP, SAFE_BOTTOM = 260, 420
HOOK_CHIP_MAX_CHARS = 38  # keep in sync with core/text.ts
CAPTION_SAFE_WIDTH = 920
CAPTION_MIN_FONT_SIZE = 42

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONTS = {
    "DejaVuSans-Bold": f"{FONT_DIR}/DejaVuSans-Bold.ttf",
    "DejaVuSans": f"{FONT_DIR}/DejaVuSans.ttf",
    "DejaVuSansMono": f"{FONT_DIR}/DejaVuSansMono.ttf",
}


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS.get(name, FONTS["DejaVuSans"])
    if not os.path.exists(path):
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def hex_to_rgb(value: str):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t: float):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def draw_background(img: Image.Image, theme: dict, scene: dict) -> None:
    """Vertical gradient standing in for the Remotion CSS gradient."""
    base = hex_to_rgb(theme["background"])
    alt = hex_to_rgb(theme["backgroundAlt"])
    draw = ImageDraw.Draw(img)
    is_lesson = theme.get("signature") == "lesson_stage"

    for y in range(0, HEIGHT, 4):
        t = y / HEIGHT
        # Lesson stage glows from the upper third; render rail sweeps corner to corner.
        weight = (1 - abs(t - 0.32) * 2.2) if is_lesson else math.sin(t * math.pi)
        weight = max(0.0, min(1.0, weight))
        draw.rectangle([0, y, WIDTH, y + 4], fill=mix(base, alt, weight * 0.85))

    accent = hex_to_rgb(theme["accent"])
    accent_soft = hex_to_rgb(theme["accentSoft"])
    if is_lesson:
        draw.rounded_rectangle(
            [(WIDTH - 720) // 2, HEIGHT - 300, (WIDTH + 720) // 2, HEIGHT - 288],
            radius=8,
            fill=accent_soft,
        )
    else:
        draw.rounded_rectangle([44, (HEIGHT - 520) // 2, 54, (HEIGHT + 520) // 2], radius=8, fill=accent)


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(draw, text, font, y, fill, shadow=True):
    w, h = text_size(draw, text, font)
    x = (WIDTH - w) // 2
    if shadow:
        draw.text((x + 3, y + 4), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=fill)
    return h


def fit_caption_font(draw, lines, font_name: str, initial_size: int):
    """Shrink until every rendered glyph run fits the 920px safe width."""
    size = initial_size
    while size > CAPTION_MIN_FONT_SIZE:
        font = load_font(font_name, size)
        if all(text_size(draw, line, font)[0] <= CAPTION_SAFE_WIDTH for line in lines):
            return font
        size -= 2
    return load_font(font_name, CAPTION_MIN_FONT_SIZE)


def draw_pill(draw, text, font, xy, bg, fg, pad=(22, 12)):
    """
    Pill with correct geometry.

    PIL's rounded_rectangle clamps a radius larger than half the shorter side,
    but passing an arbitrarily large value (999) makes short wide boxes render
    as lens/ellipse shapes rather than pills. The radius must be exactly half
    the box height.
    """
    x, y = xy
    w, h = text_size(draw, text, font)
    box_h = h + pad[1] * 2
    box_w = w + pad[0] * 2
    draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=box_h // 2, fill=bg)
    # textbbox offsets can be negative for fonts with ascenders; anchor on the
    # measured box so text sits optically centred in the pill.
    draw.text((x + pad[0], y + pad[1]), text, font=font, fill=fg, anchor="la")
    return box_h


def truncate_words(text: str, max_chars: int) -> str:
    """Mirrors truncateWords() in core/text.ts - never cut a word in half."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    out = ""
    for word in text.split():
        candidate = f"{out} {word}".strip()
        if len(candidate) > max_chars - 1:
            break
        out = candidate
    if not out:
        out = text[: max(1, max_chars - 1)]
    return out.rstrip(".,;:") + "\u2026"


def render_scene(scene: dict, spec: dict) -> Image.Image:
    theme = spec["theme"]
    img = Image.new("RGB", (WIDTH, HEIGHT), hex_to_rgb(theme["background"]))
    draw_background(img, theme, scene)
    draw = ImageDraw.Draw(img)

    text_col = hex_to_rgb(theme["text"])
    muted = hex_to_rgb(theme["textMuted"])
    accent = hex_to_rgb(theme["accent"])
    accent_soft = hex_to_rgb(theme["accentSoft"])
    bg = hex_to_rgb(theme["background"])

    # ---- captions, centred in the safe area -------------------------------
    lines = scene["captionLines"]
    caption_font = fit_caption_font(draw, lines, theme["displayFont"], 92 if scene["isCta"] else 78)
    line_h = int(caption_font.size * 1.18)
    block_h = line_h * len(lines)
    usable_top, usable_bottom = SAFE_TOP, HEIGHT - SAFE_BOTTOM
    y = usable_top + (usable_bottom - usable_top - block_h) // 2

    if scene["isHook"]:
        hook = truncate_words(spec["hookText"], HOOK_CHIP_MAX_CHARS)
        hook_font = load_font(theme["utilityFont"], 34)
        hw, hh = text_size(draw, hook, hook_font)
        draw_pill(draw, hook, hook_font, ((WIDTH - hw - 64) // 2, y - hh - 80), accent_soft, text_col, (32, 14))

    for line in lines:
        draw_centered(draw, line, caption_font, y, text_col)
        y += line_h

    if scene["isCta"]:
        cta_font = load_font(theme["displayFont"], 46)
        cw, _ = text_size(draw, spec["ctaText"], cta_font)
        draw_pill(draw, spec["ctaText"], cta_font, ((WIDTH - cw - 104) // 2, y + 48), accent, bg, (52, 22))

    # ---- placeholder provenance line --------------------------------------
    if scene["assetStatus"] == "placeholder":
        note_font = load_font(theme["utilityFont"], 26)
        note = f"[placeholder - {scene['assetType']}] {scene['visualDescription']}"
        note = note if len(note) <= 74 else note[:71] + "..."
        nw, _ = text_size(draw, note, note_font)
        draw.text(((WIDTH - nw) // 2, HEIGHT - 210), note, font=note_font, fill=muted)

    # ---- badge rail (persistent disclosures) ------------------------------
    badges = spec["badges"]
    bx, by = 56, 96
    brand_font = load_font(theme["displayFont"], 34)
    by += draw_pill(draw, badges["brand"], brand_font, (bx, by), (0, 0, 0), text_col) + 14

    if badges.get("disclosure"):
        d_font = load_font(theme["utilityFont"], 26)
        by += draw_pill(draw, badges["disclosure"], d_font, (bx, by), accent, bg, (20, 9)) + 14

    if badges.get("affiliate"):
        a_font = load_font(theme["utilityFont"], 24)
        by += draw_pill(draw, badges["affiliate"], a_font, (bx, by), (0, 0, 0), text_col, (18, 8)) + 14

    if spec["audio"]["placeholderSilence"]:
        af = load_font(theme["utilityFont"], 22)
        msg = "audio placeholder - VO not yet recorded"
        aw, _ = text_size(draw, msg, af)
        draw.text(((WIDTH - aw) // 2, HEIGHT - 150), msg, font=af, fill=muted)

    return img


def main() -> int:
    spec_path, out_path = sys.argv[1], sys.argv[2]
    thumb_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(spec_path, "r", encoding="utf8") as fh:
        spec = json.load(fh)

    fps = spec["fps"]
    tmpdir = tempfile.mkdtemp(prefix="mf_render_")
    concat_lines = []

    # One still per scene, held for the scene's exact duration. Captions are
    # per-scene in this template, so per-frame rasterisation buys nothing.
    for i, scene in enumerate(spec["scenes"]):
        frame_path = os.path.join(tmpdir, f"scene_{i:03d}.png")
        render_scene(scene, spec).save(frame_path)
        duration = scene["durationFrames"] / fps
        concat_lines.append(f"file '{frame_path}'")
        concat_lines.append(f"duration {duration:.4f}")
        if i == len(spec["scenes"]) - 1:
            # ffmpeg concat demuxer needs the last image repeated to honour its duration.
            concat_lines.append(f"file '{frame_path}'")

        if thumb_path and scene.get("isHook"):
            render_scene(scene, spec).save(thumb_path)

    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w", encoding="utf8") as fh:
        fh.write("\n".join(concat_lines) + "\n")

    total_seconds = sum(s["durationFrames"] for s in spec["scenes"]) / fps

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        # Silent stereo bed: keeps the file valid on platforms that reject
        # audio-less uploads, and reserves the VO track.
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-vf", f"fps={fps},format=yuv420p,scale={WIDTH}:{HEIGHT}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", f"{total_seconds:.4f}",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    print(json.dumps({"output": out_path, "durationSeconds": round(total_seconds, 2), "scenes": len(spec["scenes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
