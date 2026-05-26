---
id: "66"
title: "Operadores de álgebra booleana"
source_url: "https://libguides.mit.edu/c.php?g=175963&p=1158594"
fetch_url: "https://libguides.mit.edu/c.php?g=175963&p=1158594"
resolved_url: "https://libguides.mit.edu/c.php?g=175963&p=1158594"
firecrawl_title: "Boolean operators - Database Search Tips - LibGuides at MIT Libraries"
description: null
fetched_at: "2026-05-12T03:59:52.637914Z"
provider: "firecrawl"
strategy: "standard"
cache_key: "1e5b1add0c7b31563d09bc435237541fea5455fb17c1a0030d32f4e53601f245"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=UTF-8"
word_count: 466
char_count: 2930
content_sha256: "be299661981e3a382b3a7657b690660e225da84a9f76b81ae114ba99610ab8f8"
image_count: 3
link_count: 17
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

# Database Search Tips: Boolean operators

Learn strategies on effective database searching for best results.

## What to look for

Boolean operators form the basis of mathematical sets and database logic.

- They connect your search words together to either narrow or broaden your set of results.
- The three basic boolean operators are: **AND**, **OR**, and **NOT**.

### Why use Boolean operators?

- To focus a search, particularly when your topic contains multiple search terms.
- To connect various pieces of information to find exactly what you're looking for.
- Example:

  
  second creation (title) AND wilmut and campbell (author) AND 2000 (year)

## Using AND

Use AND in a search to:

- narrow your results
- tell the database that **ALL** search terms must be present in the resulting records
- example: cloning AND humans AND ethics

The purple triangle in the middle of the Venn diagram below represents the result set for this search. It is a small set using AND, the combination of all three search words.

Image summary: A three-circle Venn diagram shows the search terms cloning, ethics, and humans. The result set for AND is the small central overlap where all three circles intersect, indicating records that contain all three concepts. [Original image: and.gif](https://lgimages.s3.amazonaws.com/data/imagemanager/7506/and.gif)

Be aware:  In many, but not all, databases, the AND is implied.

- For example, Google automatically puts an AND in between your search terms.
- Though all your search terms are included in the results, they may not be connected together in the way you want.
- For example, this search: college students test anxiety is translated to: college AND students AND test AND anxiety. The words may appear individually throughout the resulting records.
- You can search using phrases to make your results more specific.
- For example: "college students" AND "test anxiety". This way, the phrases show up in the results as you expect them to be.

## Using OR

Use OR in a search to:

- connect two or more similar concepts (synonyms)
- broaden your results, telling the database that ANY of your search terms can be present in the resulting records
- example: cloning OR genetics OR reproduction

All three circles represent the result set for this search. It is a big set because any of those words are valid using the OR operator.

Image summary: A Venn diagram shows three overlapping circles labeled cloning, genetics, and reproduction. For OR searches, any record containing one or more of these terms is included, so the result set is larger than with AND. [Original image: or.gif](https://lgimages.s3.amazonaws.com/data/imagemanager/7506/or.gif)

## Using NOT

Use NOT in a search to:

- exclude words from your search
- narrow your search, telling the database to ignore concepts that may be implied by your search terms
- example: cloning NOT sheep

## Search order

Databases follow commands you type in and return results based on those commands. Be aware of the logical order in which words are connected when using Boolean operators:

- Databases usually recognize AND as the primary operator, and will connect concepts with AND together first.
- If you use a combination of AND and OR operators in a search, enclose the words to be "ORed" together in parentheses.

Examples:

- ethics AND (cloning OR reproductive techniques)
- (ethic* OR moral*) AND (bioengineering OR cloning)
