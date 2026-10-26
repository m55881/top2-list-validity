# Data licence

The data files in this repository (everything outside the code files `*.py`) are released under the Creative Commons Attribution-NonCommercial 4.0 International licence (CC BY-NC 4.0): https://creativecommons.org/licenses/by-nc/4.0/

Why non-commercial: the analysis data set (`data/derived/stanford_analysis.parquet`) and the linkage records (`linkage/`, which contain names, affiliations and metrics from the list) are adapted from the Stanford-Elsevier database. That database is licensed CC BY-NC 3.0 Unported (versions 2 and 9; https://creativecommons.org/licenses/by-nc/3.0/), which allows adaptation and redistribution with attribution for non-commercial purposes only.

Attribution for the adapted material: Ioannidis JPA, Boyack KW, Baas J. Updated science-wide author databases of standardized citation indicators. Elsevier Data Repository, version 2 (2020), DOI 10.17632/btchxktzyw.2, and version 9 (2026), DOI 10.17632/btchxktzyw.9. Licensed CC BY-NC 3.0. Changes: subset to the variables used, joined to criterion records, and derived variables added.

The code (`*.py`) is under the MIT licence (`LICENSE`).

The other sources are listed below. Reuse must also respect each source's own terms.

| Source | Used for | Terms |
|---|---|---|
| Ioannidis JPA, Boyack KW, Baas J. Updated science-wide author databases of standardized citation indicators (Elsevier Data Repository / Mendeley Data, DOI 10.17632/btchxktzyw), versions 2 (2020) and 9 (2026) | Exposure, covariates, retractions | CC BY-NC 3.0 Unported |
| US National Academy of Medicine and UK Academy of Medical Sciences election announcements, 2020-2025 | Criterion A | Public announcements |
| US National Academy of Sciences, Royal Society, TWAS election announcements, 2020-2025 | Secondary criteria | Public announcements |
| NIH RePORTER; Wellcome grants data; UKRI Gateway to Research (MRC); CIHR funding decisions; KAKEN database (JSPS); NHMRC outcomes of funding rounds; ERC funded projects | Criterion B | Each funder's open-data terms |
| Research Excellence Framework 2021 results | E6 | REF 2021 terms of use |
| World Bank income classification, via Our World in Data | Covariate | CC BY 4.0 (Our World in Data) |
| Wikidata | Secondary criteria (queries in `data/official/wikidata_queries/`) | CC0 |
