# Project icon

T3 Code project tile: a porcelain Georgia **U**, converted to outlines so the
file has no font dependency. `icon.png` (512px) is the raster fallback.

It mirrors `companion/static/favicons/project-icon.svg` exactly — same face, cap
height, baseline and corner radius — and differs only in tile colour, so the two
read as siblings. Violet because it is the one hue left unclaimed in
`companion/docs/design-language.md`; if the Companion tile changes, change this
one with it.

T3 picks the icon up from a fixed candidate list, so `assets/icon.svg` is the
match only while no `favicon.*` exists at the repo root.
