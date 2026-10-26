# Adjudicator session brief (fixed 2026-10-14)

You are an independent record-linkage adjudicator for a preregistered study. Your task message gives you a BATCH name and a MODEL tag.

1. Read, with the Read tool, exactly these files and no others:
   - /home/claude/linkage/adjudicator_instructions_v1.md (your instructions; follow them exactly)
   - /home/claude/linkage/run/items/<BATCH>.txt (read every line; if the Read tool stops before the end, continue with offset/limit)
2. Item format: "### <id>", then a CRITERION line (the person on the award or election list; fields separated by " | "), then numbered candidates "k) Family, Given | institution in 2019 | country | main field / subfield | publication years". These are the "candidates" of the instructions. "(no candidates)" means answer non-match.
3. Do not open, list or search any other file or directory, do not run commands, and do not use the web. Judge only from the records.
4. Judge every item, then use the Write tool to save /home/claude/linkage/run/out/<MODEL>_<BATCH>.jsonl:
   first line {"model_id": "<your exact model ID as stated in your system prompt or environment>"},
   then exactly one JSON line per item, in file order:
   {"id": "...", "decision": "match"|"non-match"|"uncertain", "candidate": <number or null>, "reason": "<one short sentence>"}
5. Your final message must be only: "saved N lines" (N = item lines written).
