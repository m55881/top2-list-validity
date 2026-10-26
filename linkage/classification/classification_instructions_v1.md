# Pre-linkage classification instructions (version 1, fixed 2026-10-13)

You are an independent classifier in a preregistered bibliometric study. Work alone, from the text given. Do not use any tools other than reading the files you are told to read, do not search the web, and do not use what you may recall about the people named: judge only from the text shown.

## Task A. Academy electees: research scientist or not

Each item is one person elected to the US National Academy of Medicine (NAM) or the UK Academy of Medical Sciences (AMS) in 2020–2025, with the text that followed the name in the official announcement (degrees, position, institution). Some AMS items give only an institution.

Classify the person's **main role as described** into:

- **research**: the text describes a role centred on research or academic scholarship. Examples: professor, investigator, scientist, research fellow, head of a research lab, unit, institute or research program; academic clinician with a professorial or research title; dean or department chair who also holds a professorship; a research scientist in industry. **If the text gives only an institution that is a university, research institute or hospital, classify as research.**
- **non-research**: the text describes a role centred on leadership, administration, policy, practice, journalism or law, **with no research or professorial title**. Examples: government minister, agency administrator or commissioner, public health officer, chief executive of a health system, insurer or company (without a scientific title), editor-in-chief of a journal (without a professorship), clinician in practice without an academic title, lawyer, journalist, philanthropist, investor.
- **uncertain**: the text genuinely does not allow a decision (for example, only a company or charity name with no role). Use sparingly.

The non-research class is used only in a sensitivity analysis that removes such electees, so mark someone non-research only when the text clearly supports it.

## Task B. Wellcome Investigator Awards in Humanities and Social Science: health-related or not

Each item is one award, with its exact title and a short summary of its published description.

- **yes**: the project's main subject is human health, illness, disability, medicine, health care, public health, health policy or health research (including histories, ethics, anthropology or sociology of these).
- **no**: the main subject is not health-related.
- **uncertain**: the text does not allow a decision.

## Output format (strict)

Return one JSON object per item, one per line, in the order given, and nothing else.

Task A lines: {"id": "E001", "classification": "research", "reason": "Chair of a pharmacology program at a research institute."}

Task B lines: {"id": "W01", "health_related": "yes", "reason": "History of sleep care and healthy sleep."}

Keep each reason to one short sentence. Answer every item.
