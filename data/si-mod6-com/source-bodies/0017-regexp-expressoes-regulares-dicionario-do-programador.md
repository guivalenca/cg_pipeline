---
id: "17"
title: "RegExp (Expressões Regulares) // Dicionário do Programador"
source_url: "https://www.youtube.com/watch?v=IVcbytKjL4U"
fetch_url: "https://www.youtube.com/watch?v=IVcbytKjL4U"
resolved_url: "https://www.youtube.com/watch?v=IVcbytKjL4U"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:39:36.083606Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "7a8a2ab882bd28769602e08f66a82d0481cd4b8427a1784fe380c33889fabc28"
cache_keys:
  - "7a8a2ab882bd28769602e08f66a82d0481cd4b8427a1784fe380c33889fabc28"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 514.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "9f2fdc8d00eb836e23b0e026d8d4096e2a330d0e1865778002a704898a243d05"
word_count: 1135
char_count: 7310
content_sha256: "12b8c90b71b7bf683d67912f97fa8c7567630b55326aef2f47366762aec9d700"
image_count: 10
link_count: 0
total_token_count: 34268
estimated_input_tokens: 27642
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Dicionário do Programador

**Spoken content:** The hosts welcome viewers to the "Dicionário do Programador" (Programmer's Dictionary) on Código Void TV, introducing the concept of each video covering a term, technology, or programming word.

**On-screen content:**
![Two hosts in lab coats smiling at the camera, with a "Dicionário do Programador" title card appearing later.](video-frame://17@00:00)
![Title card: Dicionário do Programador, with "RegExp" and "Em parceria com a HostGator" text.](video-frame://17@00:12)

## [00:13] What are Regular Expressions (RegExp)?

**Spoken content:** Regular expressions, also known as RegExp (Regular Expressions) or ER (Expressão Regular in Portuguese), are present in various programming languages and configuration files. They have been a part of system development since 1968.

**On-screen content:**
![Text overlay: Expressão Regular](video-frame://17@00:13)
![Text overlay: Reg Exp, Regular Expressions](video-frame://17@00:30)

## [00:46] The Origin of Regular Expressions

**Spoken content:** Regular expressions originated in the 1940s when a mathematician algebraically described a study by two neurologists on neurons. This led to a group of symbols and notation patterns. It wasn't until 20 years later that they were applied to computers, specifically with the QED text editor, which became one of the first Unix system editors. Over time, QED evolved into EGREP, a text-mode application for Linux systems used for content searches.

## [01:33] RegExp in C and Perl

**Spoken content:** In 1986, the pioneering REG-X package was created for C, allowing developers to work with regular expressions within their programs. The male host shares his first experience with REG-X while maintaining a Perl program, highlighting Perl's excellence for text processing due to its strong RegExp support.

**On-screen content:**
![Text overlay: REGEX](video-frame://17@01:44)

## [02:04] Understanding Regular Expressions and Metacharacters

**Spoken content:** In essence, RegExp is a formal method to specify a text pattern. They allow the creation of patterns to select combinations of characters in a string. While it might seem simple, it can be challenging for newcomers. The "macabre" symbols used in regular expressions are called metacharacters, which have special powers. When mixed with normal characters, they form a regular expression. Testing an expression against text determines if it matches, enabling validations, replacements, and mask creation that would be difficult with pure programming. The hosts challenge viewers to recall using an asterisk for file searches, implying a basic form of pattern matching.

**On-screen content:**
![Text overlay: Metacaracteres](video-frame://17@02:46)
![Icon: a person with glasses reading a book, with a speech bubble containing a checkmark.](video-frame://17@03:16)

## [03:18] Practical Applications and Examples

**Spoken content:** Regular expressions can create text patterns to validate various data types like dates, times, IP addresses, emails, URLs, phone numbers, CPF, credit card numbers, and more. The hosts then provide examples of complex regular expressions.

**On-screen content:**
![Example regex for date validation: ^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[012])/(12|0-9){3}$](video-frame://17@03:41)
![Example regex for IPv4 validation: ^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$](video-frame://17@03:47)

## [04:02] DDD Regular Expression Breakdown

**Spoken content:** The hosts explain a regular expression for validating a Brazilian DDD (area code). They break down each component:
*   `^` and `$` (circumflex and dollar sign): Delimit the beginning and end of the pattern (optional).
*   `()` (parentheses): Represent a group.
*   `|` (pipe): Acts as an "OR" operator, allowing for two types of DDD formats (with or without parentheses).
*   `\(` and `\)` (escaped parentheses): Used to match literal parentheses, as unescaped parentheses are metacharacters. If `?` were used after escaped parentheses, they would be optional.
*   `[0-9]` (square brackets with range): Matches any digit from 0 to 9.
*   `{2}` (curly braces with number): Specifies that exactly two occurrences of the preceding element must be present.
The explanation covers both sides of the "OR" condition in the DDD regex.

**On-screen content:**
![Example regex for DDD validation: ^(\([0-9]{2}\)\|[0-9]{2})$](video-frame://17@04:05)

## [05:33] HostGator Partnership

**Spoken content:** The "Dicionário do Programador" is a partnership with HostGator, one of the largest and best hosting companies. Viewers are encouraged to visit hostgator.com.br or use a special link in the description for a 50% discount.

**On-screen content:**
![HostGator logo with website address: www.HostGator.com.br](video-frame://17@05:33)

## [05:53] Ubiquity of Regular Expressions

**Spoken content:** Regular expressions are ubiquitous in computing. Linux users, programmers, and users of editors like Sublime Text, Brackets, or Vim have likely encountered them. They are natively present in these tools for searching files or content. Beyond built-in tools, RegExp can be used in software with almost any programming language (99.9% support them), or via external libraries if not natively supported.

## [06:31] JavaScript RegExp Example

**Spoken content:** A JavaScript example demonstrates how to create a regular expression using forward slashes instead of quotes. This specific example creates a regex that negates (using the `^` inside square brackets) any group of numbers.

**On-screen content:**
![JavaScript code example: var re = /[^0-9]/;](video-frame://17@06:31)

## [06:49] .htaccess and WordPress

**Spoken content:** The hosts mention the `.htaccess` file, widely used in systems like WordPress. This configuration file, used by Apache and PHP, defines rules for URL creation and routing, and is entirely based on regular expressions. This highlights their simplicity and power.

## [07:19] Learning Resources: Aurelio Jargas

**Spoken content:** For those interested in programming and regular expressions, the hosts recommend learning to build and read them. The first step is to choose a good book or tutorial. They express admiration for Aurelio Jargas, calling him "the guy" for regular expressions in Brazil, and encourage viewers to visit his website, aurelio.net, to explore his books and dive into the world of regular expressions. The male host shows one of Aurelio's books.

**On-screen content:**
![Book cover: Expressões Regulares - Guia de Consulta Rápida by Aurelio Jargas](video-frame://17@07:49)

## [08:02] Conclusion and Call to Action

**Spoken content:** The hosts encourage viewers to check out more content in their playlist or video description, like the video, share it with friends, subscribe to CDF TV, and join their Facebook group. They bid farewell.

**On-screen content:**
![Social media handles for the hosts and CDF TV Facebook group.](video-frame://17@08:12)

## [08:23] Blooper: Is Perl Dead?

**Spoken content:** In a blooper, the male host asks if Perl is dead, to which the female host replies, "Yes, it's dead," but then adds that it's still an excellent language for playing with regular expressions.
