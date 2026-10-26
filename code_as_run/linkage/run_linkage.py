"""Run the frozen linkage algorithm (link.py) on every criterion person against the Stanford-Elsevier
Version 2 career-long table (all 159,683 listed scientists; field restrictions are applied at analysis).
Run after OSF registration was approved (2026-10-14)."""
import sys, json, time
sys.path.insert(0, '/home/claude/linkage')
import pandas as pd
from link import StanfordIndex, link

t0 = time.time()
d = pd.read_parquet('/home/claude/data/v2_career.parquet').reset_index(drop=True)
idx = StanfordIndex(d)
ppl = pd.read_csv('/home/claude/data/derived/criterion_people.csv', keep_default_na=False)
crit = ppl.rename(columns={})[['person_id', 'source', 'first_year', 'family', 'given', 'affiliation', 'country', 'field_hint']]
crit = crit.rename(columns={'first_year': 'year'})
P, Q = link(crit, idx)
P = P.merge(ppl[['person_id', 'source']], on='person_id')
out = '/home/claude/linkage/run/'
import os; os.makedirs(out, exist_ok=True)
P.to_csv(out + 'link_persons.csv', index=False)
Q.to_csv(out + 'link_pairs.csv', index=False)
summ = P.groupby(['source', 'link_class']).size().unstack(fill_value=0)
print(summ.to_string())
print('total', P.link_class.value_counts().to_dict(), 'pairs', len(Q), 'seconds', round(time.time() - t0))
json.dump({'by_source': summ.to_dict(orient='index'), 'total': P.link_class.value_counts().to_dict(),
           'review_pairs': int(Q.person_id.isin(P[P.link_class == 'review'].person_id).sum())},
          open(out + 'link_summary.json', 'w'), indent=1, default=int)
