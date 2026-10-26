
## 2026-10-20 Quality rule for adjudicator outputs (applied before any disagreement was resolved)
Rule: an output is set aside and its batch re-run in a fresh session (same model, same brief, plus the instruction to use only the
Read and Write tools) if (a) the session reported using commands, or (b) one reason text covers >= 40% of its items (a sign of
templated, possibly mechanical answers). Set-aside files are kept in out_excluded/ for the record.
Flagged: {"opus_grant_N_b015": "top reason share 0.45", "opus_grant_N_b052": "top reason share 0.77", "opus_grant_N_b112": "top reason share 0.78; reported running a command", "sonnet_grant_N_b085": "top reason share 0.99", "sonnet_grant_N_b089": "top reason share 1.00", "sonnet_grant_N_b100": "top reason share 0.99", "sonnet_grant_N_b101": "top reason share 0.99", "sonnet_grant_N_b109": "top reason share 0.90; reported running a command"}

## 2026-10-26 Auto-match adjudication (deviation: all remaining auto-matches checked)
- sonnet auto_U_b009: session reported writing its output with Bash (forbidden) -> set aside in out_excluded/ and rerun in a fresh session.
- 40% repeated-reason rule applied to auto_U outputs; flagged: {"opus_auto_U_b002": "top reason share 0.66", "opus_auto_U_b003": "top reason share 0.92", "opus_auto_U_b004": "top reason share 0.50", "opus_auto_U_b007": "top reason share 0.64", "opus_auto_U_b008": "top reason share 0.60", "opus_auto_U_b009": "top reason share 0.54", "opus_auto_U_b011": "top reason share 0.58", "opus_auto_U_b013": "top reason share 0.52", "sonnet_auto_U_b001": "top reason share 0.90", "sonnet_auto_U_b003": "top reason share 0.94", "sonnet_auto_U_b004": "top reason share 0.93", "sonnet_auto_U_b005": "top reason share 0.92", "sonnet_auto_U_b006": "top reason share 0.93", "sonnet_auto_U_b008": "top reason share 0.90", "sonnet_auto_U_b009": "top reason share 0.42"}
- Note: out_excluded/NOTE.txt was overwritten by mistake on 2026-10-26; this audit log is the authoritative record of all set-aside outputs.

## 2026-10-26 Amendment to the repeated-reason rule for auto-match (U) batches, decided before comparing the two models
Auto-match items are mostly easy and correctly share one reason, so the 40% rule over-flags. For U batches an output is set aside
only if (a) the most frequent reason is also attached to any non-match/uncertain decision, or (b) its non-match+uncertain rate is
more than 3 SD from the mean of all U outputs, or (c) the session reported using commands.
Mean rate 0.091 (SD 0.023).
Restored under the amended rule: [["opus_auto_U_b002.jsonl", 0, 0.072], ["opus_auto_U_b003.jsonl", 0, 0.08], ["opus_auto_U_b004.jsonl", 0, 0.076], ["opus_auto_U_b007.jsonl", 0, 0.072], ["opus_auto_U_b008.jsonl", 0, 0.1], ["opus_auto_U_b009.jsonl", 0, 0.116], ["opus_auto_U_b011.jsonl", 0, 0.096], ["opus_auto_U_b013.jsonl", 0, 0.136], ["sonnet_auto_U_b001.jsonl", 0, 0.096], ["sonnet_auto_U_b003.jsonl", 0, 0.064], ["sonnet_auto_U_b004.jsonl", 0, 0.072], ["sonnet_auto_U_b005.jsonl", 0, 0.076], ["sonnet_auto_U_b006.jsonl", 0, 0.072], ["sonnet_auto_U_b008.jsonl", 0, 0.096], ["sonnet_auto_U_b009.jsonl", 0, 0.112]]
Still set aside: []

- sonnet auto_U_b015 and b016: sessions reported one no-op Bash call each (`true`, `echo`); set aside under rule (c) and rerun.

- Final check of all 54 U outputs under the amended rule: flagged [].

## 2026-10-26 Unresolved disagreements on U items
Fable unavailable (monthly spend limit). The 34 Opus-Sonnet disagreements among the extra auto-match checks are treated as not linked in the main analysis (same rule as "uncertain"); a sensitivity analysis treats them as linked. List: unresolved_disagreements.json.

## 2026-10-26 19:01 Fable tie-break for the 34 U disagreements completed after the spend limit was adjusted; the conservative not-linked rule above is no longer needed (unresolved list now empty).
