# How to apply this to affiliate-ai-agent

Nothing here touches any existing app. It is one self-contained folder.

```bash
cd /path/to/affiliate-ai-agent
git checkout main && git pull
git checkout -b agent/ai-media-factory

# unzip so the folder lands at ./media-factory/
unzip ~/Downloads/media-factory.zip -d .

git add media-factory/
git commit -m "feat: build AI media factory vertical slice"
git push -u origin agent/ai-media-factory
```

Do not merge to `main` — open a PR and review first.

## Verify before you commit

```bash
cd media-factory
npm install
npm test        # expect 113 passing
npm run demo    # writes output/<job>/*.mp4
```

## Notes

- `.gitignore` already excludes `.env`, `node_modules/`, and generated
  `data/`+`output/` contents. Only `.env.example` is tracked. No secrets.
- `output/` in this zip contains one sample render so you can watch it without
  running anything. It is gitignored, so it will not be committed.
- The sample MP4 came from the **ffmpeg fallback** renderer. Run
  `npm run remotion:ensure-browser` then `npm run demo` for the real Remotion
  output.
- Your repo currently contains only `README.md` — no Maya.exe app and no AI Tool
  Compass. Confirm this is the right repo before committing.
