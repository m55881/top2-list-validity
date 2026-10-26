"""Co-primary A (protocol Section 7): E1 sensitivity, E2 LR+/PPV, E3 AUC (DeLong), rank bands.
Run with argument 'final' (main) or 'registered' (registered-procedure links)."""
import sys, json, re
import numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/analysis'); sys.path.insert(0, '/home/claude/linkage')
from stats_utils import wilson, lr_pos, auc_ci, delong_paired, cochran_armitage
from normalize import ascii_fold, clean_given

mode = sys.argv[1] if len(sys.argv) > 1 else 'final'
col = 'stanford_row' if mode == 'final' else 'stanford_row_registered'
suffix = '' if mode == 'final' else '_reg'
S = pd.read_parquet('/home/claude/analysis/stanford_analysis.parquet')
C = pd.read_parquet('/home/claude/analysis/criterion_analysis.parquet')
meta = json.load(open('/home/claude/analysis/meta.json'))
N = meta['denominator_health']
res = {'mode': mode}


def person_ids(sub):
    """Distinct electees: linked -> Stanford row; unlinked -> normalized name (merges NAM+AMS double elections)."""
    ids = []
    for r in sub.itertuples():
        v = getattr(r, col)
        if pd.notna(v):
            ids.append(('row', int(v)))
        else:
            fam = ''.join(ch for ch in ascii_fold(r.family) if ch.isalpha())
            ids.append(('name', fam, (clean_given(r.given) or [''])[0]))
    return ids


def e1(sources, filt=None):
    sub = C[C.source.isin(sources)]
    if filt is not None:
        sub = sub[filt(sub)]
    ids = person_ids(sub)
    uniq = set(ids)
    k = sum(1 for i in uniq if i[0] == 'row')
    return len(uniq), k, wilson(k, len(uniq))


for lab, src in [('NAM_or_AMS', ['NAM', 'AMS']), ('NAM', ['NAM']), ('AMS', ['AMS'])]:
    n, k, (p, lo, hi) = e1(src)
    res[f'E1_{lab}'] = dict(electees=n, listed=k, sensitivity=p, ci=[lo, hi])

# E2 within the health sciences population
n_el, k_el, _ = e1(['NAM', 'AMS'])
A = S['A' + suffix] if ('A' + suffix) in S else S['A']
TP = int((A & S.health).sum())
listed_nonhealth = int((A & ~S.health).sum())
FN = n_el - k_el                       # electees not on the list (assumed health population; tested in S7)
FP = int(S.health.sum()) - TP
TN = int(N) - TP - FN - FP
sens = TP / (TP + FN); spec = TN / (TN + FP)
lr, llo, lhi = lr_pos(TP, FN, FP, TN)
ppv = wilson(TP, int(S.health.sum()))
res['E2'] = dict(TP=TP, FN=FN, FP=FP, TN=TN, listed_electees_outside_health=listed_nonhealth,
                 sensitivity=sens, specificity=spec, LR_pos=lr, LR_ci=[llo, lhi], PPV=ppv[0], PPV_ci=list(ppv[1:]))

# E3 discrimination within the 64,173 listed health scientists
H = S[S.health].copy(); y = A[S.health].values
c, cites, h = H['c (ns)'].values, H['nc9619 (ns)'].values, H['h19 (ns)'].values
res['E3'] = dict(n=len(H), events=int(y.sum()), auc_c=auc_ci(y, c), auc_citations=auc_ci(y, cites), auc_h=auc_ci(y, h))
a1, a2, dlt, p = delong_paired(y, c, cites); res['E3']['c_vs_citations'] = dict(diff=dlt, p=p)
a1, a2, dlt, p = delong_paired(y, c, h); res['E3']['c_vs_h'] = dict(diff=dlt, p=p)
# subfield-stratified AUC (weighted by electees)
num = den = 0.0
for sfld, g in H.assign(y=y).groupby('sm-subfield-1'):
    if 0 < g.y.sum() < len(g):
        a = auc_ci(g.y.values, g['c (ns)'].values)[0]; w = g.y.sum(); num += a * w; den += w
res['E3']['auc_c_subfield_stratified'] = num / den
# rank bands (rank of c (ns))
rk = H['rank (ns)']
band = np.select([rk <= 1000, rk <= 10000, rk <= 100000], ['1-1,000', '1,001-10,000', '10,001-100,000'], 'subfield route only')
tab = pd.DataFrame({'band': band, 'y': y}).groupby('band').y.agg(['sum', 'size'])
tab = tab.loc[['1-1,000', '1,001-10,000', '10,001-100,000', 'subfield route only']]
res['rank_bands'] = {b: dict(elected=int(r['sum']), n=int(r['size']), prop=wilson(int(r['sum']), int(r['size']))) for b, r in tab.iterrows()}
z, p = cochran_armitage(tab['sum'].values[::-1], tab['size'].values[::-1])
res['rank_trend'] = dict(z=z, p=p)
json.dump(res, open(f'/home/claude/analysis/results_A_{mode}.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
