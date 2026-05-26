# Extraction report

Short version: this is good enough for MVP annotation.

- Total source rows: 69
- Markdown files exported: 67
- Blocked/unusable sources: 2 (book/64, article/68)
- Source mix: {'article': 36, 'book': 13, 'video': 20}
- Exported mix: {'article': 35, 'book': 12, 'video': 20}
- Warnings still worth keeping in mind: browserbase_session_restarted_after_page_0011: 1, browserbase_session_restarted_after_page_0012: 3, browserbase_session_restarted_after_page_0013: 5, browserbase_session_restarted_after_page_0027: 1, intentional_blank_page_0014: 2, intentional_blank_page_0016: 2, intentional_blank_page_0030: 1, interactive_shell_requires_manual_review: 1, low_reader_word_count_page_0014: 2, low_reader_word_count_page_0016: 2, low_reader_word_count_page_0030: 1, missing_screenshot: 2, reader_low_word_count_page_0011: 1, title_error_review: 1, title_mismatch: 4

My call: do not run a separate cleaning agent for the MVP.
Let the annotation/concept extraction agent do light cleanup as it reads each source.
That means it can ignore obvious nav/OCR junk, but it should preserve page labels, timestamps, exercise numbers, examples, headings, and code blocks.

The only sources I would not feed as content are the genuinely blocked ones:
- book/64: Processando a Linguagem (manual_access_required)
- article/68: Feature Extraction in Natural Language Processing with Python (auth_wall_detected; error_page_detected; http_status_410; metadata_error)
