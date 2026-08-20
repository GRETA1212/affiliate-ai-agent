# Brands

Each brand is a directory containing:

| file | purpose |
| --- | --- |
| `brand.json` | identity, platforms, theme and **compliance rules** (validated by `BrandSchema`) |
| `signals.json` | operator-recorded opportunity signals. The scout ranks these; it never authors them. |
| `sources.json` | the approved public sources the research agent may cite |

The brand *name* is configurable — `kids-learning` is a working id, and renaming
the brand only means editing `name` in `brand.json`. Nothing in the code depends
on the display name.

To add a brand: copy a directory, change `id`/`name`, and it appears in
`npm run factory -- brands` automatically. No code change is required.
