"""Co-primary B (protocol Section 7): G1 coverage by funder (pooled, I2), G2 hit rate within the list,
G3 AUC within each funder's listed population (country-stratified pooled AUC, paired comparisons)."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/analysis'); sys.path.insert(0, '/home/claude/linkage')
from stats_utils import wilson, auc_ci, delong
from normalize import ascii_fold, clean_given

mode = sys.argv[1] if len(sys.argv) > 1 else 'final'
col = 'stanford_row' if mode == 'final' else 'stanford_row_registered'
sfx = '' if mode == 'final' else '_reg'
S = pd.read_parquet('/home/claude/analysis/stanford_analysis.parquet')
C = pd.read_parquet('/home/claude/analysis/criterion_analysis.parquet')
FUND = {'NIH_R01': ('G_NIH', ['usa']), 'Wellcome': ('G_Wellcome', ['gbr']), 'MRC': ('G_MRC', ['gbr']),
        'CIHR': ('G_CIHR', ['can']), 'KAKEN': ('G_KAKEN', ['jpn']), 'NHMRC': ('G_NHMRC', ['aus'])}
EU27 = ['aut', 'bel', 'bgr', 'hrv', 'cyp', 'cze', 'dnk', 'est', 'fin', 'fra', 'deu', 'grc', 'hun', 'irl', 'ita', 'lva',
        'ltu', 'lux', 'mlt', 'nld', 'pol', 'prt', 'rou', 'svk', 'svn', 'esp', 'swe']
ASSOC = ['nor', 'isl', 'lie', 'che', 'isr', 'tur', 'srb', 'mkd', 'mne', 'alb', 'bih', 'mda', 'ukr', 'arm', 'geo', 'tun',
         'fro', 'gbr']  # Horizon 2020 / Horizon Europe associated countries during 2020-2025 (UK associated 2020 and 2024-25)
FUND['ERC_LS'] = ('G_ERC', EU27 + ASSOC)
res = {'mode': mode}


def units(sub):
    """Distinct lead investigators: merge records linked to the same Stanford row; unlinked records by funder ID
    (person_key) and, for MRC/NHMRC, also by normalized name (their IDs are not stable across rounds)."""
    ids = set()
    for r in sub.itertuples():
        v = getattr(r, col)
        if pd.notna(v):
            ids.add(('row', int(v)))
        elif r.source in ('MRC', 'NHMRC'):
            fam = ''.join(ch for ch in ascii_fold(r.family) if ch.isalpha())
            ids.add(('name', fam, (clean_given(r.given) or [''])[0]))
        else:
            ids.add(('key', r.person_key))
    return ids


g1 = {}
for src, (flagcol, ctry) in FUND.items():
    sub = C[(C.source == src) & C.primary]
    u = units(sub); k = sum(1 for i in u if i[0] == 'row')
    g1[src] = dict(investigators=len(u), listed=k, coverage=wilson(k, len(u)))
for lab, f in [('NIH_new', lambda s: s.nih_new), ('NIH_renewal', lambda s: s.nih_renewal)]:
    sub = C[(C.source == 'NIH_R01') & f(C)]
    u = units(sub); k = sum(1 for i in u if i[0] == 'row')
    g1[lab] = dict(investigators=len(u), listed=k, coverage=wilson(k, len(u)))
# random-effects pooling on the logit scale (DerSimonian-Laird)
ks = np.array([g1[s]['listed'] for s in FUND]); ns = np.array([g1[s]['investigators'] for s in FUND])
yi = np.log(ks / (ns - ks)); vi = 1 / ks + 1 / (ns - ks); wi = 1 / vi
ybar = (wi * yi).sum() / wi.sum(); Q = (wi * (yi - ybar) ** 2).sum(); dfq = len(yi) - 1
tau2 = max(0, (Q - dfq) / (wi.sum() - (wi ** 2).sum() / wi.sum())); I2 = max(0, (Q - dfq) / Q) if Q > 0 else 0
ws = 1 / (vi + tau2); mu = (ws * yi).sum() / ws.sum(); se = np.sqrt(1 / ws.sum())
inv = lambda x: 1 / (1 + np.exp(-x))
res['G1'] = g1
res['G1_pooled'] = dict(coverage=inv(mu), ci=[inv(mu - 1.959964 * se), inv(mu + 1.959964 * se)], I2=I2, tau2=tau2, Q=Q)

# G2 and G3 within each funder's listed health population
g2, g3, strata = {}, {}, []
H = S[S.health]
for src, (flagcol, ctry) in FUND.items():
    pop = H[H.cntry.isin(ctry)]
    y = pop[flagcol + sfx].values if (flagcol + sfx) in pop else pop[flagcol].values
    g2[src] = dict(listed_health=len(pop), winners=int(y.sum()), hit_rate=wilson(int(y.sum()), len(pop)))
    if 0 < y.sum() < len(y):
        a_c = auc_ci(y, pop['c (ns)'].values); a_n = auc_ci(y, pop['nc9619 (ns)'].values); a_h = auc_ci(y, pop['h19 (ns)'].values)
        g3[src] = dict(auc_c=a_c, auc_citations=a_n, auc_h=a_h)
        aucs, cov = delong(y, [pop['c (ns)'].values, pop['nc9619 (ns)'].values, pop['h19 (ns)'].values])
        strata.append((int(y.sum()), aucs, cov))
w = np.array([s[0] for s in strata], float); w /= w.sum()
A = np.array([s[1] for s in strata]); pooled = (w[:, None] * A).sum(0)
V = sum(wi ** 2 * s[2] for wi, s in zip(w, strata))
z = 1.959964
res['G2'] = g2; res['G3'] = g3
res['G3_pooled'] = dict(auc_c=[pooled[0], pooled[0] - z * np.sqrt(V[0, 0]), pooled[0] + z * np.sqrt(V[0, 0])],
                        auc_citations=[pooled[1], pooled[1] - z * np.sqrt(V[1, 1]), pooled[1] + z * np.sqrt(V[1, 1])],
                        auc_h=[pooled[2], pooled[2] - z * np.sqrt(V[2, 2]), pooled[2] + z * np.sqrt(V[2, 2])])
from scipy import stats
for j, nm in [(1, 'citations'), (2, 'h')]:
    d = pooled[0] - pooled[j]; se = np.sqrt(V[0, 0] + V[j, j] - 2 * V[0, j])
    res['G3_pooled'][f'c_vs_{nm}'] = dict(diff=d, p=2 * stats.norm.sf(abs(d / se)))
json.dump(res, open(f'/home/claude/analysis/results_B_{mode}.json', 'w'), indent=1, default=float)


def r3(x):
    return round(float(x), 3)


print('G1 coverage:'); [print(f'  {k:12s} {v["listed"]:5d}/{v["investigators"]:6d} = {r3(v["coverage"][0])} ({r3(v["coverage"][1])}-{r3(v["coverage"][2])})') for k, v in g1.items()]
print('pooled', {k: (r3(v) if not isinstance(v, list) else [r3(x) for x in v]) for k, v in res['G1_pooled'].items()})
print('G2 hit rate:'); [print(f'  {k:10s} {v["winners"]:5d}/{v["listed_health"]:6d} = {r3(v["hit_rate"][0])}') for k, v in g2.items()]
print('G3 AUC c / citations / h:'); [print(f'  {k:10s}', [r3(v["auc_c"][0]), r3(v["auc_citations"][0]), r3(v["auc_h"][0])]) for k, v in g3.items()]
print('pooled', json.dumps(res['G3_pooled'], default=r3))
