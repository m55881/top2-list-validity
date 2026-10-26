"""Supporting models (protocol Section 7): logistic regression of recognition on standardized log c-score,
adjusting for career age (restricted cubic spline, 4 knots), field, country income group (World Bank FY2020 =
classification from 2018 GNI), self-citation %, inclusion route. Academy model (A) and grant model (funder fixed
effects, person-clustered SEs). E4 interactions: route x c, self-citation>25% x c."""
import json, numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

S = pd.read_parquet('/home/claude/analysis/stanford_analysis.parquet')
wb = pd.read_csv('/home/claude/data/wb_income2/world-bank-income-groups.csv')
wb = wb[wb.Year == 2018].dropna(subset=['Code']); wb = wb.set_index(wb.Code.str.lower())["World Bank's income classification"]
S['income'] = S.cntry.map(wb).fillna('Unclassified')
S['income'] = S.income.replace({'High-income countries': 'High', 'Upper-middle-income countries': 'Upper-middle',
                                 'Lower-middle-income countries': 'Lower-middle', 'Low-income countries': 'Low'})
H = S[S.health].copy()
H['zlogc'] = (np.log(H['c (ns)']) - np.log(H['c (ns)']).mean()) / np.log(H['c (ns)']).std()
H['zlogcit'] = (np.log1p(H['nc9619 (ns)']) - np.log1p(H['nc9619 (ns)']).mean()) / np.log1p(H['nc9619 (ns)']).std()
H['zlogh'] = (np.log(H['h19 (ns)']) - np.log(H['h19 (ns)']).mean()) / np.log(H['h19 (ns)']).std()


def rcs(x, k=4):
    """Harrell restricted cubic spline basis (knots at 5, 35, 65, 95th percentiles)."""
    t = np.percentile(x, [5, 35, 65, 95])
    def p(u): return np.maximum(u, 0) ** 3
    cols = [x]
    for j in range(k - 2):
        cols.append((p(x - t[j]) - p(x - t[k - 2]) * (t[k - 1] - t[j]) / (t[k - 1] - t[k - 2])
                     + p(x - t[k - 1]) * (t[k - 2] - t[j]) / (t[k - 1] - t[k - 2])) / (t[k - 1] - t[0]) ** 2)
    return np.column_stack(cols)


B = rcs(H.career_age.values.astype(float))
for j in range(B.shape[1]):
    H[f'age{j}'] = B[:, j]
H['selfhi'] = (H.selfpct > 25).astype(int)
# separation fixes (documented): field = health field of the main subfield (3 levels);
# 'Low' income (29 people, 0 electees) merged with 'Lower-middle'
_sf = S.groupby('sm-subfield-1')['sm-field'].agg(lambda x: x.value_counts().index[0])
H['field'] = H['sm-subfield-1'].map(_sf)
H['income'] = H.income.replace({'Low': 'Lower-middle'})
covs = 'age0 + age1 + age2 + C(field) + C(income, Treatment("High")) + selfpct + C(route)'
res = {'income_counts_health': H.income.value_counts().to_dict()}


def fit(formula, data, cluster=None):
    m = smf.logit(formula, data=data)
    r = m.fit(disp=0, maxiter=200, cov_type='cluster', cov_kwds={'groups': data[cluster]}) if cluster else m.fit(disp=0, maxiter=200)
    if not r.mle_retvals.get('converged', False):
        kw = dict(cov_type='cluster', cov_kwds={'groups': data[cluster]}) if cluster else {}
        r = m.fit(disp=0, method='bfgs', maxiter=5000, gtol=1e-8, **kw)
    conv.append((formula[:40], bool(r.mle_retvals.get('converged', False))))
    return r


conv = []


def orci(r, term):
    b, se = r.params[term], r.bse[term]
    return dict(OR=float(np.exp(b)), ci=[float(np.exp(b - 1.959964 * se)), float(np.exp(b + 1.959964 * se))], p=float(r.pvalues[term]))


H['yA'] = H.A.astype(int)
r = fit('yA ~ zlogc + ' + covs, H); res['A_OR_per_SD_logc'] = orci(r, 'zlogc'); res['A_n'] = int(r.nobs); res['A_events'] = int(H.yA.sum())
for nm, v in [('citations', 'zlogcit'), ('h', 'zlogh')]:
    rr = fit(f'yA ~ {v} + ' + covs, H); res[f'A_OR_per_SD_log{nm}'] = orci(rr, v)
ri = fit('yA ~ zlogc * C(route) + zlogc * selfhi + ' + covs.replace(' + C(route)', ''), H)
res['E4_interactions_A'] = {k: orci(ri, k) for k in ri.params.index if ':' in k}
# grant model: stack funder populations
FUND = {'G_NIH': ['usa'], 'G_Wellcome': ['gbr'], 'G_MRC': ['gbr'], 'G_CIHR': ['can'], 'G_KAKEN': ['jpn'], 'G_NHMRC': ['aus']}
EU = ['aut', 'bel', 'bgr', 'hrv', 'cyp', 'cze', 'dnk', 'est', 'fin', 'fra', 'deu', 'grc', 'hun', 'irl', 'ita', 'lva', 'ltu', 'lux',
      'mlt', 'nld', 'pol', 'prt', 'rou', 'svk', 'svn', 'esp', 'swe', 'nor', 'isl', 'lie', 'che', 'isr', 'tur', 'srb', 'mkd', 'mne',
      'alb', 'bih', 'mda', 'ukr', 'arm', 'geo', 'tun', 'fro', 'gbr']
FUND['G_ERC'] = EU
parts = []
for g, c in FUND.items():
    p = H[H.cntry.isin(c)].copy(); p['yG'] = p[g].astype(int); p['funder'] = g; parts.append(p)
G = pd.concat(parts)
rg = fit('yG ~ zlogc + C(funder) + ' + covs, G, cluster='stanford_row')
res['G_OR_per_SD_logc'] = orci(rg, 'zlogc'); res['G_rows'] = int(rg.nobs); res['G_events'] = int(G.yG.sum())
for nm, v in [('citations', 'zlogcit'), ('h', 'zlogh')]:
    rr = fit(f'yG ~ {v} + C(funder) + ' + covs, G, cluster='stanford_row')
    res[f'G_OR_per_SD_log{nm}'] = orci(rr, v)
res['converged'] = conv
json.dump(res, open('/home/claude/analysis/results_models.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=lambda v: round(float(v), 4)))
