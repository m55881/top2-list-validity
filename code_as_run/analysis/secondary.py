"""Secondary (E4, E5, E7, E8) and sensitivity analyses (S1, S3, S4, S5, S8, S9, S10, S11, S12, S13, S14, S15)
on the final links, plus the registered-procedure links (deviation check). Protocol Sections 7-8."""
import sys, json, re
import numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/analysis'); sys.path.insert(0, '/home/claude/linkage')
from stats_utils import wilson, lr_pos, auc_ci, delong_paired
from normalize import ascii_fold, clean_given, split_stanford

S = pd.read_parquet('/home/claude/analysis/stanford_analysis.parquet')
C = pd.read_parquet('/home/claude/analysis/criterion_analysis.parquet')
aw = pd.read_csv('/home/claude/data/derived/criterion_awards.csv', keep_default_na=False, low_memory=False)
meta = json.load(open('/home/claude/analysis/meta.json'))
res = {}
r3 = lambda x: round(float(x), 3)


def pid(r, col='stanford_row'):
    v = getattr(r, col)
    if pd.notna(v):
        return ('row', int(v))
    fam = ''.join(ch for ch in ascii_fold(r.family) if ch.isalpha())
    return ('name', fam, (clean_given(r.given) or [''])[0])


def sens(sub, col='stanford_row', listed_rows=None):
    u = {pid(r, col) for r in sub.itertuples()}
    k = sum(1 for i in u if i[0] == 'row' and (listed_rows is None or i[1] in listed_rows))
    return dict(n=len(u), listed=k, sensitivity=wilson(k, len(u)))


def auc_block(mask_pop, y, score='c (ns)'):
    pop = S[mask_pop]; yy = y[mask_pop].values
    if not (0 < yy.sum() < len(yy)):
        return None
    return dict(n=len(pop), events=int(yy.sum()), auc=auc_ci(yy, pop[score].values))


A = C[C.source.isin(['NAM', 'AMS'])]
# ---- S1: c with self-citations included
res['S1_A_auc_c_with_selfcites'] = auc_block(S.health, S.A, 'c')
res['S1_A_auc_c_ns'] = auc_block(S.health, S.A, 'c (ns)')
# ---- S3: exclude contested links (treat as not linked and drop from denominator)
Ac = A[~(A.contested == True)]
res['S3_E1'] = sens(Ac)
res['S3_auc'] = auc_block(S.health & ~S.A_contested, S.A)
# ---- S4: NAM only / AMS only AUC
res['S4_auc_NAM'] = auc_block(S.health, S.A_NAM); res['S4_auc_AMS'] = auc_block(S.health, S.A_AMS)
# ---- S5: exclude non-research electees
A5 = A[A.role_class != 'non-research']
res['S5_E1'] = sens(A5)
res['S5_auc'] = auc_block(S.health, S.A_research_only)
# ---- S8: exclude 2020 elections and awards
years = aw.groupby('person_key').year.agg(lambda s: set(s.astype(int)))
C['years'] = C.person_key.map(years)
late = C.years.map(lambda ys: any(y >= 2021 for y in ys) if isinstance(ys, set) else False)
res['S8_E1'] = sens(A[late[A.index]])
rows_late = set(C[late & C.source.isin(['NAM', 'AMS']) & C.stanford_row.notna()].stanford_row.astype(int))
res['S8_auc'] = auc_block(S.health, S.stanford_row.isin(rows_late))
# ---- S9: probabilistic bias analysis for missed links (false-negative rate among unlinked)
rng = np.random.default_rng(20261026)
e1 = sens(A)
for fnr in (0.02, 0.05, 0.10):
    n, k = e1['n'], e1['listed']
    # among the n-k unlinked electees, a fraction fnr (uniform 0.5-1.5 x) were truly listed but missed
    draws = []
    for _ in range(5000):
        f = fnr * rng.uniform(0.5, 1.5)
        extra = rng.binomial(n - k, f)
        draws.append(rng.beta(k + extra + 0.5, n - k - extra + 0.5))
    res[f'S9_E1_fnr_{fnr}'] = dict(median=float(np.median(draws)), interval=[float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))])
# ---- S10 and E7: TWAS
ce = pd.read_csv('/home/claude/data/derived/criterion_elections.csv')
tw = ce[ce.source == 'TWAS']
res['E7_by_year'] = {int(y): dict(n=len(g), metric_any=wilson(int(g.twas_metric_any.sum()), len(g)),
                                  stanford_top2=wilson(int(g.twas_stanford_top2.sum()), len(g)),
                                  h_index=wilson(int(g.twas_h_index.sum()), len(g)))
                     for y, g in tw.groupby('year')}
from stats_utils import cochran_armitage
gy = tw.groupby('year').agg(k=('twas_metric_any', 'sum'), n=('twas_metric_any', 'size'))
res['E7_trend'] = dict(zip(['z', 'p'], cochran_armitage(gy.k.values, gy.n.values)))
T = C[C.source == 'TWAS'].copy()
T['key2'] = T.family.str.strip() + '|' + T.given.str.strip()
tw2 = tw.assign(key2=tw.family.str.strip() + '|' + tw.given.str.strip()).drop_duplicates('key2').set_index('key2')
T['metric'] = T.key2.map(tw2.twas_metric_any).fillna(False).astype(bool)
res['E7_twas_sensitivity_all'] = sens(T)
res['S10_twas_excl_metric'] = sens(T[~T.metric])
res['E7_twas_sensitivity_metric_citing'] = sens(T[T.metric])
# ---- E8: all science with C2 (NAS or Royal Society)
C2 = C[C.source.isin(['NAS', 'RoyalSociety'])]
e8 = sens(C2)
TP = int(S.C2.sum()); FN = e8['n'] - e8['listed']; FP = len(S) - TP; TN = int(meta['denominator_all']) - TP - FN - FP
lr = lr_pos(TP, FN, FP, TN)
res['E8'] = dict(E1=e8, LR_pos=lr, PPV=wilson(TP, len(S)), auc_c=auc_ci(S.C2.values, S['c (ns)'].values),
                 auc_citations=auc_ci(S.C2.values, S['nc9619 (ns)'].values), auc_h=auc_ci(S.C2.values, S['h19 (ns)'].values))
res['E8']['c_vs_citations_p'] = delong_paired(S.C2.values, S['c (ns)'].values, S['nc9619 (ns)'].values)[3]
# ---- E4: heterogeneity by inclusion route and self-citation (AUC within subgroups; sensitivity by route)
for lab, m in [('route_top100k', S.route == 'top100k'), ('route_subfield_only', S.route == 'subfield_only'),
               ('selfcite_le25', S.selfpct <= 25), ('selfcite_gt25', S.selfpct > 25)]:
    res[f'E4_auc_{lab}'] = auc_block(S.health & m, S.A)
res['E4_share_electees_listed_by_route'] = {r: int((S.A & S.health & (S.route == r)).sum()) for r in ('top100k', 'subfield_only')}
# ---- E5 integrity: link 2019 listed to 2026 (Version 9): same normalized name, firstyr +-1, same main field
v9 = pd.read_parquet('/home/claude/data/v9_career.parquet')
def nk(a):
    f, g = split_stanford(a)
    return ''.join(ch for ch in ascii_fold(f) if ch.isalpha()) + '|' + ' '.join(clean_given(g))
v9['nk'] = v9.authfull.map(nk); S['nk'] = S.authfull.map(nk)
cand = S[['stanford_row', 'nk', 'firstyr', 'sm-field']].merge(v9[['nk', 'firstyr', 'sm-field', 'np6025_rw']].reset_index(), on='nk', suffixes=('', '_9'))
cand = cand[((cand.firstyr - cand.firstyr_9).abs() <= 1) & (cand['sm-field'] == cand['sm-field_9'])]
nlink = cand.groupby('stanford_row').size()
uniq = cand[cand.stanford_row.isin(nlink[nlink == 1].index)].set_index('stanford_row')
S['retracted'] = S.stanford_row.map(uniq.np6025_rw.gt(0))
res['E5_crossversion'] = dict(linked_unique=int(len(uniq)), ambiguous=int((nlink > 1).sum()), unlinked=int(len(S) - nlink.size))
H = S[S.health & S.retracted.notna()]
band = np.select([H['rank (ns)'] <= 1000, H['rank (ns)'] <= 10000, H['rank (ns)'] <= 100000], ['1-1,000', '1,001-10,000', '10,001-100,000'], 'subfield route only')
res['E5_retraction_by_band'] = {b: wilson(int(g.retracted.sum()), len(g)) for b, g in H.assign(band=band).groupby('band')}
res['E5_retraction_by_election'] = {str(e): wilson(int(g.retracted.sum()), len(g)) for e, g in H.groupby('A')}
HH = S[S.health]
res['E5_selfcite_gt25_by_election'] = {str(e): wilson(int((g.selfpct > 25).sum()), len(g)) for e, g in HH.groupby('A')}
res['E5_selfcite_gt40_by_election'] = {str(e): wilson(int((g.selfpct > 40).sum()), len(g)) for e, g in HH.groupby('A')}
res['E5_selfcite_gt25_overall'] = wilson(int((HH.selfpct > 25).sum()), len(HH))
# ---- S11: broaden population (add Biology and Psychology & Cognitive Sciences, by subfield majority field)
sf = S.groupby('sm-subfield-1')['sm-field'].agg(lambda s: s.value_counts().index[0])
broad = set(sf[sf.isin({'Clinical Medicine', 'Biomedical Research', 'Public Health & Health Services', 'Biology', 'Psychology & Cognitive Sciences'})].index)
res['S11_auc'] = auc_block(S['sm-subfield-1'].isin(broad), S.A)
# ---- grant sensitivity analyses (AUC within funder populations, coverage)
FC = {'G_NIH': ['usa'], 'G_CIHR': ['can'], 'G_KAKEN': ['jpn'], 'G_NHMRC': ['aus'], 'G_MRC': ['gbr'], 'G_Wellcome': ['gbr']}
res['S12_career15_auc'] = {g: auc_block(S.health & S.cntry.isin(c) & (S.career_age >= 15), S[g]) for g, c in FC.items()}
res['S13_NIH_renewal_auc'] = auc_block(S.health & (S.cntry == 'usa'), S.G_NIH_renewal)
res['S13_NIH_new_auc'] = auc_block(S.health & (S.cntry == 'usa'), S.G_NIH_new)
cb = C[C.source == 'CIHR']
res['S14_CIHR_coverage_incl_bridge'] = sens(cb)
res['S14_CIHR_auc_incl_bridge'] = auc_block(S.health & (S.cntry == 'can'), S.G_CIHR_incl_bridge)
kk = aw[(aw.source == 'KAKEN')]
drop = kk.kaken_section.astype(str).str.contains('中区分39|中区分42|中区分45')
keep_keys = set(kk[~drop].person_key)
K15 = C[(C.source == 'KAKEN') & C.person_key.isin(keep_keys)]
res['S15_KAKEN_coverage'] = sens(K15)
rows15 = set(K15[K15.stanford_row.notna()].stanford_row.astype(int))
res['S15_KAKEN_auc'] = auc_block(S.health & (S.cntry == 'jpn'), S.stanford_row.isin(rows15))
json.dump(res, open('/home/claude/analysis/results_secondary.json', 'w'), indent=1, default=lambda x: float(x) if np.isscalar(x) else str(x))
print(json.dumps(res, indent=0, default=lambda x: r3(x) if np.isscalar(x) else str(x))[:9000])
