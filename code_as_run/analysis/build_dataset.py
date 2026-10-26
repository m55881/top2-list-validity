"""Analysis dataset (protocol Sections 5 and 7).
Outputs:
  stanford_analysis.parquet  one row per 2019 career-long listed scientist (159,683) with exposure,
                             covariates and recognition outcomes (linked criterion people)
  criterion_analysis.parquet one row per criterion person with link status
"""
import json, pandas as pd, numpy as np
D = '/home/claude/'
d = pd.read_parquet(D + 'data/v2_career.parquet').reset_index(drop=True)
d['stanford_row'] = d.index
H = {'Clinical Medicine', 'Biomedical Research', 'Public Health & Health Services'}
sf = d.groupby('sm-subfield-1')['sm-field'].agg(lambda s: s.value_counts().index[0])
HS = sorted(sf[sf.isin(H)].index)
d['health'] = d['sm-subfield-1'].isin(HS)
d['route'] = np.where((d['rank (ns)'] <= 100000) | (d['rank'] <= 100000), 'top100k', 'subfield_only')
d['career_age'] = 2019 - d.firstyr
d['papers_per_year'] = d.np6019 / (d.career_age + 1)
d['selfpct'] = d['self%'] * 100

ppl = pd.read_csv(D + 'data/derived/criterion_people.csv', keep_default_na=False)
F = pd.read_csv(D + 'linkage/run/final_links.csv')
R = pd.read_csv(D + 'linkage/run/final_links_registered.csv')
cls = pd.read_csv(D + 'linkage/classification/electee_classification.csv')
aw = pd.read_csv(D + 'data/derived/criterion_awards.csv', keep_default_na=False)

crit = ppl.merge(F[['person_id', 'stanford_row', 'contested', 'linked']], on='person_id', how='left')
crit = crit.merge(R[['person_id', 'stanford_row']].rename(columns={'stanford_row': 'stanford_row_registered'}), on='person_id', how='left')
# NIH: new vs competing renewal per person
nih = aw[aw.source == 'NIH_R01'].groupby('person_key').category.agg(lambda s: set(s))
key_by_pid = ppl.set_index('person_id').person_key
crit['nih_new'] = crit.apply(lambda r: r.source == 'NIH_R01' and 'new' in nih.get(key_by_pid[r.person_id], set()), axis=1)
crit['nih_renewal'] = crit.apply(lambda r: r.source == 'NIH_R01' and 'renewal' in nih.get(key_by_pid[r.person_id], set()), axis=1)
# primary = has at least one primary award (excludes CIHR bridge-only people)
crit['primary'] = crit.any_primary.astype(str).str.lower().isin(['true', '1'])
# non-research electees (NAM/AMS) from the pre-linkage classification
cls['raw_key'] = cls.source + '|' + cls.family + '|' + cls.given
crit['raw_key'] = crit.source + '|' + crit.family + '|' + crit.given
crit = crit.merge(cls[['raw_key', 'final', 'contested']].rename(columns={'final': 'role_class', 'contested': 'role_contested'}),
                  on='raw_key', how='left')
crit.to_parquet(D + 'analysis/criterion_analysis.parquet')


def flag(sources, col='stanford_row', extra=None):
    sub = crit[crit.source.isin(sources) & crit[col].notna()]
    if extra is not None:
        sub = sub[extra(sub)]
    return set(sub[col].astype(int))


out = d.copy()
for name, srcs in {'A_NAM': ['NAM'], 'A_AMS': ['AMS'], 'C2_NAS': ['NAS'], 'C2_RS': ['RoyalSociety'], 'C3_TWAS': ['TWAS'],
                   'G_NIH': ['NIH_R01'], 'G_MRC': ['MRC'], 'G_Wellcome': ['Wellcome'], 'G_KAKEN': ['KAKEN'],
                   'G_NHMRC': ['NHMRC'], 'G_ERC': ['ERC_LS']}.items():
    out[name] = out.stanford_row.isin(flag(srcs, extra=lambda s: s.primary))
    out[name + '_reg'] = out.stanford_row.isin(flag(srcs, 'stanford_row_registered', extra=lambda s: s.primary))
out['G_CIHR'] = out.stanford_row.isin(flag(['CIHR'], extra=lambda s: s.primary))
out['G_CIHR_reg'] = out.stanford_row.isin(flag(['CIHR'], 'stanford_row_registered', extra=lambda s: s.primary))
out['G_CIHR_incl_bridge'] = out.stanford_row.isin(flag(['CIHR']))
out['G_NIH_new'] = out.stanford_row.isin(flag(['NIH_R01'], extra=lambda s: s.nih_new))
out['G_NIH_renewal'] = out.stanford_row.isin(flag(['NIH_R01'], extra=lambda s: s.nih_renewal))
out['A'] = out.A_NAM | out.A_AMS
out['A_reg'] = out.A_NAM_reg | out.A_AMS_reg
out['C2'] = out.C2_NAS | out.C2_RS
out['A_research_only'] = out.stanford_row.isin(flag(['NAM', 'AMS'], extra=lambda s: s.role_class != 'non-research'))
out['A_contested'] = out.stanford_row.isin(flag(['NAM', 'AMS'], extra=lambda s: s.contested == True))
out.to_parquet(D + 'analysis/stanford_analysis.parquet')
meta = {'health_subfields': HS, 'n_listed': len(out), 'n_health': int(out.health.sum()),
        'denominator_health': float(d[d.health].groupby('sm-subfield-1')['sm-subfield-1 count'].first().sum()),
        'denominator_all': float(d.groupby('sm-subfield-1')['sm-subfield-1 count'].first().sum())}
json.dump(meta, open(D + 'analysis/meta.json', 'w'), indent=1)
print({k: v for k, v in meta.items() if k != 'health_subfields'})
print(out[[c for c in out.columns if c.startswith(('A', 'G_', 'C2', 'C3')) and not c.endswith('_reg')]].sum().to_string())
print('linked rows shared by >1 criterion person per source:',
      crit[crit.stanford_row.notna()].groupby(['source', 'stanford_row']).size().gt(1).groupby(level=0).sum().to_dict())
