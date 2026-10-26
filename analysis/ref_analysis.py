"""E6: listed 2019 health scientists per submitted Main Panel A FTE vs FTE-weighted Main Panel A outputs GPA."""
import numpy as np, pandas as pd, json
from scipy import stats
x = pd.read_excel('data/reference/ref/ref2021.xlsx', header=6, engine='calamine')
x.columns = ['ukprn','inst','sort','panel','uoa_n','uoa','ms_letter','ms_name','joint','profile','fte','fte_total','pct_elig','s4','s3','s2','s1','u']
A = x[(x.panel == 'A') & (x.profile == 'Outputs')].copy()
for c in ['fte','s4','s3','s2','s1']: A[c] = pd.to_numeric(A[c], errors='coerce')
A['gpa'] = (4*A.s4 + 3*A.s3 + 2*A.s2 + 1*A.s1) / 100
inst = A.groupby('ukprn').apply(lambda g: pd.Series({'fte': g.fte.sum(), 'gpa': np.average(g.gpa, weights=g.fte)}))
M = pd.read_csv('data/reference/ref/ref_institution_map.csv'); S = pd.read_parquet('data/derived/stanford_analysis.parquet')
h = S[(S.cntry=='gbr') & S.health].merge(M[M.ukprn.notna()], left_on='inst_name', right_on='stanford_inst')
inst['listed'] = h.groupby('ukprn').size()
inst['listed'] = inst.listed.fillna(0)
inst['per_fte'] = inst.listed / inst.fte
d = inst[inst.fte > 0]
rho = stats.spearmanr(d.per_fte, d.gpa).correlation
rng = np.random.default_rng(20261026); bs = []
for _ in range(2000):
    s = d.sample(len(d), replace=True, random_state=rng.integers(1e9)); bs.append(stats.spearmanr(s.per_fte, s.gpa).correlation)
# partial Spearman adjusting for log FTE: residualize ranks
r = d[['per_fte','gpa']].rank(); z = np.log(d.fte).rank()
def resid(a): b = np.polyfit(z, a, 1); return a - np.polyval(b, z)
pr = np.corrcoef(resid(r.per_fte), resid(r.gpa))[0,1]
n = len(d); t = pr*np.sqrt((n-3)/(1-pr**2)); p_pr = 2*stats.t.sf(abs(t), n-3)
res = dict(institutions=n, listed_mapped=int(d.listed.sum()), spearman=rho, ci=[float(np.percentile(bs,2.5)), float(np.percentile(bs,97.5))],
           p=stats.spearmanr(d.per_fte, d.gpa).pvalue, partial_spearman_logFTE=pr, partial_p=p_pr)
json.dump(res, open('results/results_E6.json','w'), indent=1, default=float); print(json.dumps(res, indent=1, default=lambda v: round(float(v),4)))
