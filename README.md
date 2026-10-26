# Top 2% List Validity: Code and Data

Code, derived data and full record-linkage audit trail for:

> Alotaibi MM. Validity of the Stanford–Elsevier Top 2% List as a Marker of Excellence in Health Sciences Research: A Preregistered Prospective Criterion-Validity Study. *Manuscript submitted to JAMA Network Open.*

Preregistration: Open Science Framework, approved October 14, 2026 (embargoed until December 31, 2026). DOI: `[to add]`.

## What the study does

The study fixes membership of the 2019 career-long Stanford–Elsevier list (version 2, May 2020 data freeze). It then asks whether membership and the composite c-score identify the health scientists who, from 2020 to 2025, were:

- **Co-primary A:** elected to the US National Academy of Medicine (NAM) or the UK Academy of Medical Sciences (AMS); or
- **Co-primary B:** awarded, as lead investigator, a major competitive grant by NIH (R01), Wellcome, MRC, CIHR, JSPS KAKENHI (S)/(A), NHMRC or the ERC.

## Repository layout

| Folder | Contents |
|---|---|
| `analysis/` | Analysis scripts: dataset build, co-primary A and B, secondary and sensitivity analyses, logistic models, REF 2021 analysis, shared statistics |
| `results/` | JSON output of every analysis. The manuscript numbers come from these files |
| `data/derived/` | Analysis-ready data: `stanford_analysis.parquet` (159,683 listed scientists with exposure, covariates and outcomes) and `criterion_analysis.parquet` (35,340 recognized persons with link status), plus the standardized criterion lists |
| `data/official/` | Academy election lists as retrieved from official announcements, plus the Wikidata queries and raw query output used for the secondary criteria |
| `data/reference/` | World Bank income groups (Our World in Data extract), REF 2021 results, and the frozen Stanford-to-REF institution map |
| `linkage/` | Frozen linkage algorithm, adjudicator instructions, 400-pair benchmark, electee role classification and the full adjudication run (`linkage/run/`) |
| `scripts/` | Parsers that turned source files into the derived lists |

## Reproducing the analysis

Requirements: Python 3.13 with the packages in `requirements.txt`. All commands run from the repository root.

The derived data in `data/derived/` are enough to rerun every analysis except S2 (single-year list) and the retraction analysis (E5). Those need the source Stanford–Elsevier tables (below).

```bash
pip install -r requirements.txt
python analysis/coprimary_A.py final        # E1-E3, rank bands
python analysis/coprimary_A.py registered   # same, registered-procedure links
python analysis/coprimary_B.py final        # G1-G3
python analysis/coprimary_B.py registered
python analysis/models.py                   # adjusted odds ratios, E4 interactions
python analysis/ref_analysis.py             # E6, REF 2021
python analysis/secondary.py                # E4-E8, S1, S3-S5, S8-S15 (needs data/stanford/v9_career.parquet)
python analysis/sensitivity_S2.py           # S2 (needs v2 career and single-year tables)
```

To rebuild the derived data from the source tables, run `python analysis/build_dataset.py` first.

A full rerun on October 26, 2026 reproduced both derived data files and every file in `results/` byte for byte.

### Source data not redistributed here

| File expected | Source |
|---|---|
| `data/stanford/v2_career.parquet`, `v2_single.parquet` | Version 2 (2020) of “Updated science-wide author databases of standardized citation indicators”, Tables S6 and S7, DOI 10.17632/btchxktzyw.2. Convert with `scripts/to_parquet.py` |
| `data/stanford/v9_career.parquet` | 2026 version of the same database (career-long table) |
| `data/grants_raw/` | Funder award lists (NIH RePORTER, Wellcome, UKRI Gateway to Research, CIHR, KAKEN, NHMRC, ERC). Only needed to rerun `linkage/standardize_criteria.py`; the standardized lists are in `data/derived/criterion_awards.csv` |

URLs, retrieval dates and checksums for every source file are listed in the OSF registration.

## Record linkage and AI adjudication

The source database has no author identifiers, so recognized persons were linked by name, institution, country and field.

1. **Algorithm.** `linkage/normalize.py` and `linkage/link.py` were frozen before linkage. Their checksums are in `linkage/FROZEN_linkage_code.sha256`, and `sha256sum -c` passes for the 5 code and instruction files from `linkage/`. The adjudicator briefs it lists live in `linkage/run/`. `agent_brief_v2.md` is listed twice: the first hash is an earlier draft, and the second matches the file used.
2. **Benchmark.** `linkage/benchmark/` holds 400 synthetic pairs: 200 altered true matches and 200 different people with the same family name and initial. It also holds both models’ answers and the results.
3. **Adjudication.** Claude Opus 5.5 and Claude Sonnet 5.5 judged every case independently. Claude Fable 5.1 settled disagreements. To keep the repository small enough for web upload, the large folders are zipped in `linkage/run/`, with checksums in `ARCHIVES.sha256`:
   - `adjudication_items.zip`: inputs given to the models (`items/`)
   - `adjudication_outputs.zip`: accepted outputs (`out/`, `out_tiebreak/`)
   - `adjudication_set_aside.zip`: every output that was set aside, never deleted (`out_excluded/`, `out_superseded/`, `out_rejected/`, `out_quarantine/`, `out_void/`, `out_discarded/`)

   Unzip them in `linkage/run/` before rerunning the linkage scripts. The merged tables are `linkage/run/combined_*.csv`, and the final links are `linkage/run/final_links.csv` (main analysis) and `final_links_registered.csv` (registered procedure).
4. **Audit trail.** The reasons for every set-aside output are in `linkage/run/audit_log.md` (the authoritative record), `PROCEDURE_NOTES.md`, `QC_rule.md`, `incident_log.md` and `process_deviations.log`.

## Changes from the code as run

The only change to the archived scripts was path handling:

- Absolute workspace paths (`/home/claude/...`) were rewritten as paths relative to the repository root.
- The scripts exactly as run, with their original absolute paths, are kept in `code_as_run/`.
- `analysis/sensitivity_S2.py` was written for this archive to record the S2 analysis, which was first run interactively.
  - It reproduces the reported S2 values for academies (54.9%, 509 of 927) and all-field academies (75.4%).
  - For NIH it counts distinct investigators as in G1 (24,401). The interactive run grouped unlinked NIH awardees by name (24,098; coverage 16.8% vs 16.6%).

## Deviations from the registered plan

These are reported in the manuscript (Methods and eTable 1):

1. All 6,598 remaining automatic matches were adjudicated, because precision in the registered 200-match sample was 0.93. Results under the registered procedure are reported as a sensitivity analysis.
2. Two changes removed complete separation in the logistic models:
   - field was grouped by the field of each scientist’s main subfield;
   - low-income countries were merged with lower-middle-income countries.
3. S6 (prize records) and S7 (electees with at least 5 papers) were not run.

## Licences

- **Code:** MIT (`LICENSE`).
- **Derived data and linkage records:** CC BY 4.0 (`DATA_LICENSE.md`), subject to the terms of the upstream sources listed there.
- **Personal data:** The criterion lists contain names and affiliations as published by academies and funders. They are shared only to allow verification of the linkage.

## Use of AI

Claude Opus 5.5, Claude Sonnet 5.5 and Claude Fable 5.1 (Anthropic) adjudicated record linkage and classified electee roles. Claude Opus 5.5 wrote the analysis code under the author’s direction. The author reviewed the code and outputs and is responsible for them. Full statement: manuscript, Article Information.

## Citation

See `CITATION.cff`.
