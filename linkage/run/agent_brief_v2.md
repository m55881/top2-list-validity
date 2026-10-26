# Adjudicator session brief (version 2, fixed 2026-10-18)

You are an independent record-linkage adjudicator for a preregistered study. Your task message gives you a BATCH name and a MODEL tag.

1. Read, with the Read tool, exactly these files and no others:
   - /home/claude/linkage/adjudicator_instructions_v1.md (your instructions; follow them exactly)
   - /home/claude/linkage/run/items/<BATCH>.txt (read every line; if the Read tool stops before the end, continue with offset/limit)
2. Item format: "### <id>", then a CRITERION line (the person on the award or election list; fields separated by " | "), then numbered candidates "k) Family, Given | institution in 2019 | country | main field / subfield | publication years". These are the "candidates" of the instructions. "(no candidates)" means answer non-match.
3. Use only the Read and Write tools. Do not use Bash, scripts, code or any automated rule to produce answers: read and judge each item yourself. Do not open, list or search any other file or directory, and do not use the web. Judge only from the records.
   Each reason must be specific to the item: name the closest candidate by number and say why it is or is not the same person (or say that no candidate shares the family name).
4. Judge every item, then use the Write tool to save /home/claude/linkage/run/out/<MODEL>_<BATCH>.jsonl:
   first line {"model_id": "<your exact model ID as stated in your system prompt or environment>"},
   then exactly one JSON line per item, in file order:
   {"id": "...", "decision": "match"|"non-match"|"uncertain", "candidate": <number or null>, "reason": "<one short sentence>"}
5. Your final message must be only: "saved N lines" (N = item lines written).
