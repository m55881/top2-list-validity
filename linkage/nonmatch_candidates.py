"""For each algorithm non-match, find the 10 most similar Stanford names (protocol Section 6) and measure
how similar the best one is. Similarity: Jaro-Winkler on normalized 'family given-first' strings, searched
within the same family-name first 3 letters (plus exact family match on any initial)."""
import sys, json; sys.path.insert(0,'./linkage')
import pandas as pd
from rapidfuzz.distance import JaroWinkler
from normalize import split_stanford, ascii_fold, clean_given
d=pd.read_parquet('data/stanford/v2_career.parquet').reset_index(drop=True)
fg=d.authfull.map(split_stanford)
d['nf']=fg.map(lambda x:''.join(c for c in ascii_fold(x[0]) if c.isalpha()))
d['ng']=fg.map(lambda x:(clean_given(x[1]) or [''])[0])
d['key']=d.nf+' '+d.ng
pref={}
for i,f in zip(d.index,d.nf): pref.setdefault(f[:3],[]).append(i)
P=pd.read_csv('run/link_persons.csv'); ppl=pd.read_csv('./data/derived/criterion_people.csv',keep_default_na=False)
nm=P[P.link_class=='non-match'].merge(ppl,on=['person_id','source'])
rows=[]
for r in nm.itertuples(index=False):
    f=''.join(c for c in ascii_fold(r.family) if c.isalpha()); g=(clean_given(r.given) or [''])[0]
    q=f+' '+g; cand=pref.get(f[:3],[])
    sc=sorted(((JaroWinkler.similarity(q,d.at[i,'key']),i) for i in cand),reverse=True)[:10]
    rows.append(dict(person_id=r.person_id,source=r.source,best_sim=sc[0][0] if sc else 0.0,
        same_family_any_initial=any(d.at[i,'nf']==f for _,i in sc), top10=[int(i) for _,i in sc], top10_sim=[round(s,3) for s,_ in sc]))
R=pd.DataFrame(rows); R.to_json('run/nonmatch_top10.json',orient='records')
import numpy as np
for t in [0.85,0.90,0.95]: print(t, (R.best_sim>=t).sum())
print('same family, any initial:', R.same_family_any_initial.sum())
print(R.assign(hi=R.best_sim>=0.90).groupby('source').hi.agg(['sum','count']).to_string())
