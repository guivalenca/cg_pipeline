# Extraction report

Short version: this is good enough for MVP annotation.

- Total source rows: 44
- Markdown files exported: 43
- Blocked/unusable sources: 1 (book/6)
- Source mix: {'article': 30, 'book': 1, 'video': 13}
- Exported mix: {'article': 30, 'video': 13}
- Warnings still worth keeping in mind: blank_or_unreadable_screenshot: 1, expected_pdf_but_metadata_not_pdf: 1, local_whisper_fallback: 1, manual_qa_text_body_usable: 1, missing_screenshot: 10, title_mismatch: 1, unexpected_content_type: 1

My call: do not run a separate cleaning agent for the MVP.
Let the annotation/concept extraction agent do light cleanup as it reads each source.
That means it can ignore obvious nav/OCR junk, but it should preserve page labels, timestamps, exercise numbers, examples, headings, and code blocks.

The only sources I would not feed as content are the genuinely blocked ones:
- book/6: Chapter 1 - Results in the rearview mirror may seem greater than they are, pages 19 to 45 (manual_access_required)
