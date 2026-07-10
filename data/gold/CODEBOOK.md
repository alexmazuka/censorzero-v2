# Gold-standard codebook — parket / non-parket

Committed before annotation begins (PREREGISTRATION.md section 9). Annotation
is **blind**: the annotator sees only the article title and body text — never
the URL, date, rubric, period, or the classifier's output.

## The judgment

For each article, decide a single label:

- **parket** — the item is a one-sided official-record piece: it is framed
  around the activity or statement of a **Ukrainian** state official or body,
  its factual content rests on a **single** official source, and it contains
  **no** alternative, independent, expert, or opposing voice. This mirrors
  IMI's public description: material that "акцентує на діяльності певних
  посадовців", covering an event "виключно з офіційної позиції посадовців, не
  надаючи простору для альтернативної чи експертної оцінки."
- **non-parket** — anything else: it carries more than one source, or a
  non-official / expert / opposing voice, or it is not framed around a
  domestic official, or it has no official actor at all.

## Decision rules (apply in order)

1. **No domestic-official framing → non-parket.** If the piece is not centred
   on a Ukrainian official or state body (e.g. it is about weather, sport,
   culture, an ordinary citizen, a company, or a *foreign* official), label
   non-parket regardless of sourcing. Foreign officials (NATO, EU, G7, foreign
   ministers/leaders, «МЗС РФ») do **not** make an item parket.
2. **Any genuine second voice → non-parket.** If an expert, analyst,
   opposition figure, affected citizen, NGO, or a second independent official
   is quoted or paraphrased with their own assessment, label non-parket — even
   if an official is the main actor.
3. **Military situation reports → non-parket (record the reason).** Front-line
   summaries, air-raid notices, and General-Staff daily briefings are
   structurally single-source by nature. They are annotated **non-parket** and
   tagged `military_bulletin` so the with/without-ATO scenarios can be checked.
4. **Single official source, official framing, no second voice → parket.**
   A report built entirely on one Ukrainian official's statement/announcement
   with no other perspective is parket. IMI's own example — an article on a
   minister visiting a brigade, relaying only his words — is the prototype.
5. **Unclear / cannot tell from the text → non-parket** and tag `uncertain`.
   Do not guess parket; the conservative label is non-parket.

## What is NOT considered

- Tone, whether the coverage is flattering, or whether the official is from the
  governing party — irrelevant. Parket is about single-sourced official framing,
  not sentiment.
- Article length. A long single-source official piece is still parket; a short
  two-source piece is not.
- Whether the topic is "important." Newsworthiness is not judged here.

## Recorded fields per article

`id`, `label` (parket|non_parket), `military_bulletin` (bool),
`uncertain` (bool), `note` (free text, optional). Nothing else.

## Worked examples

- *"Міністр оборони відвідав бригаду «Хартія» і подякував воїнам"*, body
  relays only the minister's remarks → **parket** (rule 4).
- *"Битва за Україну. День 622-й"*, General-Staff daily summary → **non-parket**,
  `military_bulletin` (rule 3).
- *"Уряд ухвалив програму, — Шмигаль. Економіст Іваненко: бракує фінансування"*
  → **non-parket** (rule 2, second voice).
- *"Міністр фінансів Німеччини прибув до Києва"*, only his statement → **non-parket**
  (rule 1, foreign official).
- *"У Києві оголосили повітряну тривогу"*, no official actor → **non-parket**
  (rule 1).
