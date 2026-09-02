# Companion package handoff

The CG Pipeline only authors and downloads a selected Graph Revision. Lesson Preview
generation, final validation, and installation remain manual Companion operations.

Run the CG Pipeline web process with access to a Companion checkout and the Python
environment that has Companion's dependencies. A sibling `companion/` checkout is found
automatically; otherwise set `COMPANION_REPO`. Set `COMPANION_PYTHON` when Companion uses
a different interpreter. `COMPANION_DATABASE_URL` and `COMPANION_PLATFORM_SCHEMA` are
passed to the validator without exposing the CG Pipeline database as Companion state.

## 1. Pick and download a Graph Revision

Open a Lesson Build for the intended Lesson Subject. Under **Graph Revision**, choose
**Baixar pacote Companion** for the current revision, or expand **Histórico de revisões**
and download the package for an earlier revision.

The application runs Companion's package validator before returning the download. A
blocked package shows the validation message in the active Lesson Build dialog; the
adjacent raw `graph.json` view and download remain available for diagnosis.

Unpack the ZIP into a staging directory. It must contain one directory named after the
graph ID with exactly these files:

```text
graph-…/
├── graph.json
└── intro_notes.json
```

The downloaded `intro_notes.json` is intentionally empty and schema-valid. At this
point Companion can load the graph, but it returns no Lesson Preview.

## 2. Generate Lesson Previews in Companion

From the Companion checkout, point the generator at the unpacked graph and replace the
empty artifact in place:

```sh
python -m scripts.lesson_intro_notes.cli generate \
  /absolute/path/to/graph-…/graph.json \
  --output /absolute/path/to/graph-…/intro_notes.json
```

The generator requires Companion's `DATABASE_URL` and its configured
`OPENROUTER_API_KEY_COMPANION`; it records the generation through Companion's cost
ledger. Keep the generated `intro_notes.json` beside the exact `graph.json` revision it
was generated from.

## 3. Validate the completed package

Run Companion's validator against the staging directory that contains the graph-ID
directory:

```sh
python scripts/validate_graph_package.py /absolute/path/to/staging-root
```

If that graph ID is already installed, make the replacement explicit:

```sh
python scripts/validate_graph_package.py \
  /absolute/path/to/staging-root \
  --replace-graph-id graph-…
```

Continue only when the JSON result has `"accepted": true`. A nonzero exit or any issue
code is a blocker.

## 4. Install manually

Stop the Companion process that reads the filesystem Graph Catalog. Back up any
existing `reference/graphs/graph-…` directory, then copy the validated graph-ID
directory into `reference/graphs/`. Start Companion again and confirm that the Graph
Catalog resolves the graph and its Lesson Previews before removing the backup.

CG Pipeline never writes to Companion's checkout, database, or Graph Catalog.
