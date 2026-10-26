# Adjudicator output quality-control rule (fixed 2026-10-15, during the run, before any outcome analysis)

Trigger found: some outputs reuse one reason for most items. Agreement alone cannot detect blanket answers,
because most non-match items have no true match.

Rule: an output is rejected and its batch rerun in a fresh session with the same brief if more than 50% of
its items share one identical reason AND, for those items, the reason is not verifiably true (an item has at
least one candidate whose family name is identical and whose given name is compatible after normalization).
Rejected outputs are kept (renamed *.rejected) and archived. The rerun replaces them. Applied to all outputs
at the end of the run; counts reported.
