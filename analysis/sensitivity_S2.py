"""S2 (protocol Section 8): replace the 2019 career-long list with the 2019 single-year list.
Career rows are carried to the single-year list by exact (authfull, inst_name, cntry); a criterion person counts as
listed when their linked career row is also on the single-year list."""
import sys, json
import pandas as pd
sys.path.insert(0, 'analysis'); sys.path.insert(0, 'linkage')
from stats_utils import wilson
from normalize import ascii_fold, clean_given

c = pd.read_parquet('data/stanford/v2_career.parquet').reset_index(drop=True)
s = pd.read_parquet('data/stanford/v2_single.parquet')
k = ['authfull', 'inst_name', 'cntry']
rows = set(c.reset_index().merge(s[k].drop_duplicates(), on=k)['index'])
C = pd.read_parquet('data/derived/criterion_analysis.parquet')


def ids(sub, by_key=False):
    out = set()
    for r in sub.itertuples():
        if pd.notna(r.stanford_row):
            out.add(('row', int(r.stanford_row)))
        elif by_key:
            out.add(('key', r.person_key))
        else:
            fam = ''.join(ch for ch in ascii_fold(r.family) if ch.isalpha())
            out.add(('name', fam, (clean_given(r.given) or [''])[0]))
    return out


res = {'career_rows_found_in_single_list': len(rows), 'single_list_size': len(s)}
for lab, src, bk in [('S2_E1_A', ['NAM', 'AMS'], False), ('S2_E1_C2', ['NAS', 'RoyalSociety'], False)]:
    u = ids(C[C.source.isin(src)], bk); n1 = sum(1 for i in u if i[0] == 'row' and i[1] in rows)
    res[lab] = dict(n=len(u), listed_single=n1, sensitivity=list(wilson(n1, len(u))))
u = ids(C[(C.source == 'NIH_R01') & C.primary], True); n1 = sum(1 for i in u if i[0] == 'row' and i[1] in rows)
res['S2_G1_NIH'] = dict(n=len(u), listed_single=n1, coverage=list(wilson(n1, len(u))))
json.dump(res, open('results/results_S2.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
