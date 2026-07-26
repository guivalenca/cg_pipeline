-- image_summary: a paragraph our own ingestion wrote to describe an image,
-- marked by the 'Image summary:' prefix the extractor emits. It is the one
-- place where an artifact body carries model output instead of the author's
-- words, and provenance must be able to tell the two apart: a task citing an
-- image_summary block is answered by our description of the author's image,
-- not by the source directly.
--
-- The rule change makes this blocker version 2; existing version-1 rows stand
-- untouched beside the new sets, as the ledger requires.

ALTER TABLE block DROP CONSTRAINT block_kind_check;
ALTER TABLE block ADD CONSTRAINT block_kind_check CHECK (
    kind IN ('paragraph','heading','code_block','list_item','image','image_summary','table','blockquote')
);
