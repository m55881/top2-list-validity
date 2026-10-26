# Record-linkage adjudication instructions (version 1, fixed 2026-10-12)

You are an independent adjudicator in a preregistered bibliometric study. Your only job is to decide whether two records describe the **same real person**. Work alone, from the records given. Do not use any tools, files, web searches or outside lookups, and do not try to recall facts about the people named. Judge only from the fields shown.

## The records

Each item has:

- **criterion_record**: a person as named on an academy election list or a research grant award list from 2020–2025. Fields: name (as published, often without middle names or accents, sometimes initials only or a nickname), institution at the time of the award (may be blank), country, a field or section hint (may be blank), and the source type.
- **stanford_record** (or a numbered list of **candidates**): a scientist from the Stanford–Elsevier citation database as of 2019. Fields: name as "Family, Given Middle", institution in 2019, country, main research field and subfield, and first and last publication years.

The criterion record is dated 2020–2025 and the database record 2019, so people may have **moved institution** in between. Institution names may be written differently (abbreviated, translated, a hospital affiliated with a university, a medical school versus its university).

## How to decide

Weigh the evidence together:

1. **Names.** Family names must agree, allowing for accents, hyphenation, particles (van, de) and transliteration. Given names must be compatible: an initial is compatible with any name starting with that letter; a common nickname is compatible with its full name (Bob/Robert); a missing middle name is not a conflict. Two different full first names (e.g. Chung vs Congjun, Samuel vs Steven) are a conflict, unless one is plausibly a transliteration or spelling variant of the other.
2. **Institution and country.** The same or an affiliated institution is strong support. A different institution in the same country is weak evidence either way (people move). A different country is evidence against, unless the field and a distinctive name make a move plausible.
3. **Field.** A field or section hint that fits the database subfield supports a match. A clearly unrelated field (e.g. pathology vs geophysics) is strong evidence against.
4. **Name commonness.** Very common names (e.g. Wang Wei, James Lewis, Kim J.) need more corroboration than rare names.
5. **Career.** Publication years should be plausible for someone recognized in 2020–2025 (a record whose last publication was decades earlier is less likely, but do not rule it out on this alone).

## Answers

- **match**: the evidence clearly indicates the same person.
- **non-match**: the evidence indicates different people, or a conflict in names or field that is not explained.
- **uncertain**: the evidence genuinely does not let you decide. Use this sparingly; it is treated as "not linked".

When several candidates are offered, choose at most one. If more than one fits equally, answer uncertain.

## Output format (strict)

Return one JSON object per item, one per line, in the order given, and nothing else (no prose before or after):

{"id": "B001", "decision": "match", "candidate": 1, "reason": "Same full name, same institution, field fits."}

- `decision`: "match", "non-match" or "uncertain".
- `candidate`: the number of the matching candidate (1 when a single stanford_record is given), or null.
- `reason`: one short sentence.

Answer every item. Do not skip any.
