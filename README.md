# Concept Graph Pipeline

Local pipeline for turning assigned course materials into runtime Concept Graph
artifacts.

The repository contains extraction scripts, source manifests, pipeline stage
code, prompts, documentation, and generated graph artifacts used to build and
review course concept graphs.

## Structure

- `creation/`: Python package for the concept graph creation pipeline.
- `video/`, `book/`, `article/`: source-specific acquisition and preprocessing
  scripts.
- `extraction/`: organized source markdown before and after image
  preprocessing.
- `runs/`: named pipeline run artifacts.
- `docs/`: planning notes, design documents, and visualizations.
- `prompts/`: prompt assets used by the pipeline.
- `source/`: workbook export helpers and source spreadsheets.

## Development

Run creation pipeline tests from the `creation` package:

```bash
cd creation
python3 -m pytest
```

Run the current deterministic smoke pipeline:

```bash
cd creation
PYTHONPATH=src python3 -m concept_graph_creation.cli \
  --run-id prototype-smoke \
  --deterministic-fixture \
  --validation-failure-demo
```

See `creation/README.md` for phase-specific commands and the expected run
artifact layout.
