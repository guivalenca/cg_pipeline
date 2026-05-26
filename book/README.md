# Book Browserbase pipeline

Captures assigned Minha Biblioteca book pages as paired evidence images and
markdown transcripts. The local script owns scope normalization, cache keys,
validation, and artifact layout. Browserbase only provides the authenticated
cloud browser session.

## Setup

Install the shared pipeline dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

Configure Browserbase and DeepSeek in `cg_pipeline/.env` or the repository `.env`:

```bash
BROWSERBASE_API_KEY=...
BROWSERBASE_PROJECT_ID=...
BROWSERBASE_CONTEXT_ID=...
DEEPSEEK_API_KEY_ADMIN=...
```

Library credentials can use the same OpenClaw convention as the VPS runner. Put
the username/password in a small JSON file:

```json
{
  "LIBRARY_USERNAME": "...",
  "LIBRARY_PASSWORD": "...",
  "SOPHIA_TERMINAL_URL": "https://philos.sophia.com.br/terminal/9418"
}
```

Then point OpenClaw at it through `~/.openclaw/openclaw.json`:

```json
{
  "secrets": {
    "providers": {
      "concept_graph_library": {
        "source": "file",
        "mode": "json",
        "path": "~/path/to/library.json",
        "maxBytes": 8192
      }
    }
  }
}
```

You can also bypass OpenClaw with either `CG_PIPELINE_LIBRARY_CREDENTIALS_FILE`
or direct environment variables:

```bash
CG_PIPELINE_LIBRARY_CREDENTIALS_FILE=/absolute/path/to/library.json
CG_PIPELINE_LIBRARY_USERNAME=...
CG_PIPELINE_LIBRARY_PASSWORD=...
SOPHIA_TERMINAL_URL=https://philos.sophia.com.br/terminal/9418
```

`BROWSERBASE_CONTEXT_ID` is optional. If it is not set, the script creates a
Browserbase Context and writes the id to `cg_pipeline/book/browserbase_context.json`.
Use one persistent context for this library login and avoid running two book
captures against the same context concurrently.

Browserbase does not automatically know how to log in. The script encodes the
same state machine used by the VPS runner: open Sophia, authenticate through the
`loginModal` iframe, search `#PalavraChave` by `resource_code`, extract
`codigoSubcampo`, call `IntegracaoDigital/ExecutarSingleSignOn`, and only accept
a Minha Biblioteca reader URL for the requested book. CAPTCHA, MFA, wrong-book
handoffs, expired access, or missing search results stop as `needs_manual`.

## Run

```bash
python3 cg_pipeline/book/extract_books.py
python3 cg_pipeline/book/extract_books.py --only 15,18 --force
python3 cg_pipeline/book/extract_books.py --only 15 --refresh-cache --force
```

`url.json` contains the workbook rows with `id`, `title`, `resource_code`, and
the assignment `description`. DeepSeek normalizes that description into a
concrete page scope before the Browserbase session starts. If the description
does not resolve to explicit page labels, the item is marked `needs_manual`.

## Output

Artifacts are written under `cg_pipeline/book/output/{id}/`:

- `{id}-{slug}.md`: combined per-page markdown with frontmatter.
- `evidence/page_0001.png`: screenshot evidence for each requested page.
- `pages/page_0001.md`: OCR/accessibility text captured from the reader frame.
- `request.json`: redacted source request.
- `metadata.json`: normalized scope, requested pages, cache key, and status.
- `source_manifest.json`: source identity and coverage used.
- `page_manifest.json`: ordered page labels, reader page ids, and file paths.
- `gate_report.json`: coverage and artifact validation.
- `acquisition_result.json`: Browserbase acquisition status and warnings.

Successful bundles are copied to `cg_pipeline/book/cache/{cache_key}/`. The
cache key includes the book id, resource code, source URL, normalized scope,
scope prompt version, and capture version. Re-running the same exact scope
replays the cached bundle unless `--refresh-cache` is set.

Manual-access failures are intentional stops. CAPTCHA, MFA, expired access,
restricted titles, or wrong-reader handoffs produce `needs_manual` artifacts
instead of retries that could cache the wrong book or fabricated content.
