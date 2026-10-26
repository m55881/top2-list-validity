"""E6 step 1: map Stanford UK institution names (2019 health listed) to REF 2021 institutions, using names only
(protocol Section 7: mapping built before REF profiles are examined). Hospitals, NHS trusts, research councils,
companies and the federal 'University of London' are left unmapped."""
import re, sys
import pandas as pd
sys.path.insert(0, '/home/claude/linkage')
from normalize import ascii_fold

x = pd.read_excel('/home/claude/analysis/ref/ref2021.xlsx', header=6, engine='calamine', usecols=[0, 1])
inst = x.dropna().drop_duplicates()
inst.columns = ['ukprn', 'name']


def norm(s):
    s = ascii_fold(s).replace('&', ' and ')
    s = re.sub(r'[^a-z ]', ' ', s)
    return ' '.join(s.split())


def keys(name):
    base = name.split(' / ')[0]
    base = re.sub(r'\(the\)|, the$|^the ', '', base, flags=re.I).strip()
    n = norm(base); out = {n}
    m = re.match(r'university of (.+)', n)
    if m:
        out.add(m.group(1) + ' university')
    return out


K = {}
for r in inst.itertuples():
    for k in keys(r.name):
        K[k] = r.ukprn
ALIAS = [  # (regex on normalized Stanford name, REF institution name)
    (r'\bucl\b|university college london', 'University College London'),
    (r'imperial college|national heart and lung institute', 'Imperial College of Science, Technology and Medicine'),
    (r'barts and the london|queen mary', 'Queen Mary University of London'),
    (r'newcastle university|university of newcastle', 'University of Newcastle upon Tyne'),
    (r"queen s university belfast|queens university belfast", "Queen's University of Belfast"),
    (r'king s college london|kings college london', "King's College London"),
    (r'st george s university of london|st georges university of london', "St. George's Hospital Medical School"),
    (r'keele university', 'University of Keele'), (r'ulster university', 'University of Ulster'),
    (r'durham university', 'University of Durham'), (r'lancaster university', 'The University of Lancaster'),
    (r'royal holloway', 'Royal Holloway and Bedford New College'),
    (r'institute of cancer research', 'Institute of Cancer Research: Royal Cancer Hospital (The)'),
    (r'london school of hygiene', 'London School of Hygiene and Tropical Medicine'),
    (r'nuffield department|weatherall institute|sir william dunn school|kennedy institute of rheumatology|wellcome centre for human genetics|university of oxford', 'University of Oxford'),
    (r'cambridge institute for medical research|gurdon institute|university of cambridge', 'University of Cambridge'),
    (r'warwick medical school', 'The University of Warwick'),
    (r'edinburgh medical school|university of edinburgh', 'University of Edinburgh'),
    (r'brighton and sussex medical school', 'University of Sussex'),
    (r'hull york medical school', 'University of York'),
]
EXCLUDE = r'\bnhs\b|hospital|infirmary|medical research council|\bmrc\b|public health england|plc|\bltd\b|journal|crick|sanger|babraham|bioinformatics institute|john innes|^university of london$'
name_by_id = dict(zip(inst.ukprn, inst.name)); id_by_name = {v: k for k, v in name_by_id.items()}

S = pd.read_parquet('/home/claude/analysis/stanford_analysis.parquet')
uk = S[S.cntry == 'gbr'].inst_name.dropna().unique()
rows = []
for s in uk:
    n = norm(s); hit = None; how = ''
    for pat, refname in ALIAS:
        if re.search(pat, n):
            hit = id_by_name[refname]; how = 'alias'; break
    if hit is None and not re.search(EXCLUDE, n):
        cands = [(k, v) for k, v in K.items() if (' ' + k + ' ') in (' ' + n + ' ')]
        if cands:
            k, v = max(cands, key=lambda kv: len(kv[0])); hit = v; how = 'name'
    rows.append(dict(stanford_inst=s, ukprn=hit, ref_name=name_by_id.get(hit), method=how))
M = pd.DataFrame(rows)
M.to_csv('/home/claude/analysis/ref/ref_institution_map.csv', index=False)
hs = S[(S.cntry == 'gbr') & S.health]
mapped = hs.inst_name.isin(M[M.ukprn.notna()].stanford_inst)
print('UK health listed', len(hs), 'mapped', int(mapped.sum()), round(mapped.mean(), 3), '| institutions reached', M.ukprn.nunique())
print(hs[~mapped].inst_name.value_counts().head(25).to_string())
