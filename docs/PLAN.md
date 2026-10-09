# Plan: from 152 photos to a text knowledge base

**Goal.** Answer exam questions from a set of Techcombank documents. The documents arrived as 152
phone photos of a laptop screen (`docs/source/`, kept out of git). This plan turns them into a
**text-only knowledge base** that a RAG app can search and cite. The RAG app itself is the next plan.

## What the photos are

Surveyed by hand, 10 of 152:

- **Photos, not screenshots.** All are 2560×1920, taken at an angle, with glare and moiré. Text is
  readable by eye, but this is harder than a clean scan.
- **The order is scrambled.** The number at the end of each file name runs 1–152, but that is the
  order of the export, not the order of the pages. Photo 1 is page 14 of a 15-page PDF.
- **Most photos say where they came from.** The browser shows the file path
  (`4.HTVH/<folder>/<uuid>.pdf`) and the page number (`14 / 15`). That is enough to group the photos
  into documents and to put the pages in order.
- **There are several kinds of page:**
  - slides, in Vietnamese and in English, a few with large photos and little text;
  - FAQ tables (STT | Câu hỏi | Câu trả lời);
  - dense text pages in Word, two pages per photo, with no path or page number visible.
- **Not every page was photographed.** For example, one deck has 60 pages and only some of them
  appear. The knowledge base must say which pages are missing, so that a missing answer is not
  mistaken for "the document doesn't say".

## Decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Markdown only.** One `.md` file per source document. Each page is a `## Trang N` section. Tables become Markdown tables; slides become headings and bullets. | Markdown is plain text that an LLM reads natively. Tables survive. The page is the natural unit for a citation ("Homecare FAQ, trang 14"). |
| D2 | **No images in the knowledge base.** A visual becomes one line of text (`> Hình: logo Masterise, OneHousing, Techcombank`). An image is kept only when its meaning can't be written down, such as a complex diagram. Then the page gets `critical_image: true` and a written summary, and you decide. | You asked for text. Text is searchable; an image isn't. |
| D3 | **Reading uses a vision model, once.** An operonx Job runs one item per photo. Each photo goes through `LLMOp` (`messages=` with an `image_url` block, already supported) and comes back as JSON: path, page, total pages, title, the page as Markdown, and anything unreadable. The results are cached per photo, so a rerun only redoes what failed. | There is no text layer to extract from a photo. A vision model handles the angle, the glare and Vietnamese diacritics better than classic OCR. This is to be confirmed in P1 against Tesseract (`vie`). |
| D4 | **The model is chosen by measurement.** I transcribe 6 varied photos by hand: an FAQ table, a Word page, an English slide, a Vietnamese slide, a photo-heavy slide, and a blurry one. 3–4 vision models on OpenRouter are scored against that, on character errors, table cells, and whether path and page are right. The pick is the cheapest model that is accurate enough. | The first test shows how models differ on Vietnamese photos. Even the most expensive candidate costs only a few dollars for 152 photos. |
| D5 | **Grouping is by file path; ordering is by page number.** Photos with no path (Word, PowerPoint) are grouped by window title and running headings, and ordered by photo number. A page photographed twice is kept once: the clearer copy, with gaps filled from the other. | The path in the address bar is the most reliable key there is. |
| D6 | **Every file has a header.** It gives the title, the source folder, the pages present and the pages missing, and whether a person has checked it (`reviewed: true`). A rerun never overwrites a reviewed file. | It shows the coverage of each document, and protects hand corrections. |
| D7 | **Index and glossary.** `kb/INDEX.md` lists every document: one-line summary, page coverage and topics. `kb/glossary.md` lists the abbreviations (CBNV, CASA, HENRYs, …) with their meanings, as found in the documents. | Exam questions often use an abbreviation where the text spells it out, or the reverse. |
| D8 | **`kb/` stays out of git**, like the photos. | The content is internal Techcombank material and this repo is public. To share it, it's one line to change in `.gitignore`. |

## Phases

Each phase ends with a check that has to pass, measured, before the next one starts.

**P1 — Choose how to read the photos.**
- I write the 6 hand transcriptions.
- I write `src/reading/`: the prompt and JSON schema, and `read_photo_flow` (load the photo → `LLMOp`
  → validate).
- I score 3–4 models, plus Tesseract as a baseline, on the 6 photos.
- *Gate:* the chosen model gets ≥ 98% of characters right on the text pages, ≥ 95% of table cells,
  and 6/6 on path and page.

**P2 — Read all 152 photos.**
- The `read_photos` Job runs over every photo, and writes one JSON file per photo to `kb/_pages/`.
- A second, cheaper pass rereads the numbers, dates and names on each page and flags any
  disagreement.
- *Gate:* every photo is either read or listed as failed with a reason. The cost and the time are
  reported.

**P3 — Build the documents.**
- `assemble`: group, order, deduplicate, then write `kb/<folder>/<slug>.md`, `INDEX.md` and
  `glossary.md`.
- *Gate:* every page from P2 lands in exactly one document, and every document lists its missing
  pages.

**P4 — Review.**
- I check, against the photo:
  - every flagged page;
  - every table;
  - a random 15% of the rest.
- I correct the Markdown by hand and mark the file reviewed.
- *Gate:* on the random sample, no wrong number or name remains. Every correction is logged in
  `docs/REVIEW.md`.

**P5 — A question set, the gate for the RAG app.**
- About 40 questions with their answers and source pages. They are drafted from the knowledge base,
  then each one is checked against the photo by me.
- Add any real exam questions or past papers your wife has; these are the best test.
- *Gate:* stored as `eval/questions.jsonl`. The RAG plan will use it to measure retrieval and
  answers.

## Open questions

- **Does your wife have sample exam questions or the exam format** (multiple choice or written)?
  They make the best P5 set, and they decide how the RAG app should answer.
