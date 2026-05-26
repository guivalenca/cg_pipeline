# Firecrawl article acquisition

Fetches the NLP course article URLs with Firecrawl and writes auditable artifacts for later cleaning, annotation, and concept extraction.

## Setup

`cg_pipeline/.env` must contain:

```sh
FIRECRAWL_API_KEY=fc-...
```

Install dependencies from the repo root:

```sh
python3 -m pip install -r requirements.txt
```

## Run

Default run, skipping articles that already have markdown in `cg_pipeline/article/firecrawl/output/{id}/`:

```sh
python3 cg_pipeline/article/firecrawl/scrape_articles.py
```

Regenerate output artifacts from the local request cache:

```sh
python3 cg_pipeline/article/firecrawl/scrape_articles.py --force
```

Force a new Firecrawl request and rebuild the cache:

```sh
python3 cg_pipeline/article/firecrawl/scrape_articles.py --force --refresh
```

When a normal Firecrawl scrape fails transiently, the scraper automatically
tries one Firecrawl-only minimal retry before failing the article. This retry
requests markdown only, skips screenshot/link/image extraction, relaxes
`onlyCleanContent`, uses a 240 second Firecrawl timeout, and sends Portuguese,
Spanish, and English language hints. The retry is configured in
`routes.json` under `minimal_retry`.

Fetch only selected ids:

```sh
python3 cg_pipeline/article/firecrawl/scrape_articles.py --only 6,22,36
```

Use a different input file:

```sh
python3 cg_pipeline/article/firecrawl/scrape_articles.py --input path/to/url.json
```

## Output

Each article gets its own folder:

```text
cg_pipeline/article/firecrawl/output/{id}/
```

Artifacts written per fetched article:

- `{id}-{slug}.md` - cleaned markdown with YAML frontmatter
- `raw_response.json` - full Firecrawl response
- `request.json` - exact Firecrawl request body
- `http_response.json` - HTTP status and headers from the Firecrawl API call
- `metadata.json` - Firecrawl page metadata
- `gate_report.json` - deterministic source-trust checks
- `screenshot.png` or similar - render proof, when Firecrawl returns a screenshot URL

Batch diagnostics:

```text
cg_pipeline/article/firecrawl/output/run_log.jsonl
cg_pipeline/article/firecrawl/output/summary.json
```

The local request cache lives in:

```text
cg_pipeline/article/firecrawl/.cache/
```

The cache key is based on the normalized URL, Firecrawl route strategy, and request parameters. This keeps downstream re-runs from spending credits unless `--refresh` is passed.

## Routing Config

Edit `routes.json` to add or change host-specific behavior without touching code.

Current route groups:

- `blocked_hosts` - rejected up front, for auth-walled sources like `philos.sophia.com.br`
- `interactive_hosts` - pages such as `course.spacy.io` and `kaggle.com` that need manual review even after rendering
- `static_with_actions_hosts` - pages that benefit from waits before extraction, such as Medium properties
- `app_ui_hosts` - template-heavy or application-like pages where `onlyCleanContent` and boilerplate stripping matter
- `pdf_overrides` - per-id PDF parser mode overrides; id `46` forces OCR

Inline markdown image references are preserved in the Firecrawl artifact. The
source-body preparation step copies raw article markdown into
`cg_pipeline/extraction/pre-image/`; OpenAI-backed image preprocessing then
rewrites article images into text or plain provenance links under
`cg_pipeline/extraction/post-image/`.

Set an OpenAI credential before running image preprocessing:

```sh
export OPENAI_API_KEY_ADMIN=...
# standard SDK fallback is also supported:
export OPENAI_API_KEY=...
```

Run image preprocessing after organizing extraction files:

```sh
python3 cg_pipeline/article/preprocess_images.py
```

This writes `cg_pipeline/article/image-preprocessing/{id}-*.manifest.json`
and `summary.json`. If OpenAI is unavailable or rate-limited for an article,
embedded images are still rewritten as plain unavailable image links and the
manifest/index record is marked `processed_with_errors`.

Or run it as part of extraction organization:

```sh
python3 cg_pipeline/organize_extraction.py --clean --preprocess-article-images
```

Screenshots are only for audit gates and are not substituted into the markdown body.
