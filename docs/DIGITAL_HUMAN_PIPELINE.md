# Persistent Digital Human Pipeline

The affiliate media factory supports a reusable creator identity through an Unreal/MetaHuman adapter.

## Goal

Use the same approved virtual creator across many TikTok/YouTube Shorts instead of generating a different face every time.

```text
script + voice
    ↓
MetaHuman audio-driven facial animation
    ↓
reusable approved creator identity
    ↓
Unreal Level Sequence
    ↓
Movie Render Queue
    ↓
vertical creator MP4
    ↓
assets/media/generated/<campaign>/
    ↓
premium video assembler
```

## Required Unreal setup

The Unreal project must already contain:

1. one approved MetaHuman identity;
2. a vertical creator camera/lighting setup;
3. a Level Sequence containing the creator;
4. a Movie Render Queue config;
5. project-side automation that reads `CREATOR_REQUEST_PATH` and writes the final video to `CREATOR_OUTPUT_PATH`.

MetaHuman Animator supports offline facial animation from audio. Movie Render Queue supports command-line rendering and Python executors, so the project-side automation can later import the generated voice file, solve facial animation, bind it to the sequence, and render without manual editing.

## Environment

```text
DIGITAL_HUMAN_PROVIDER=unreal-metahuman
DIGITAL_HUMAN_ID=maya-creator-v1
UNREAL_EDITOR_CMD=C:\Program Files\Epic Games\UE_5.x\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
UNREAL_PROJECT=C:\path\CreatorStudio.uproject
UNREAL_LEVEL_SEQUENCE=/Game/Creator/LS_VerticalCreator
UNREAL_MOVIE_PIPELINE_CONFIG=/Game/Creator/MRQ_Vertical1080x1920
```

Keep the provider disabled until the Unreal project is ready:

```text
DIGITAL_HUMAN_PROVIDER=disabled
```

## Asset contract

A successful render becomes:

```text
assets/media/generated/<campaign-slug>/00-<creator-id>.mp4
```

Because generated human footage is not verified product evidence, actual product appearance must still come from vendor/product media or real screen capture.

## Identity policy

- Reuse one approved creator identity across renders.
- Do not imitate a real person's likeness without permission.
- Do not fabricate testimonials or first-hand product use.
- Generated creator footage requires human review before publishing.
- Product claims must remain grounded in verified sources.
