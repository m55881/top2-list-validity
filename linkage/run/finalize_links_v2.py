"""Final links after the deviation (all auto-matches adjudicated).
Every person with a candidate is decided by the adjudicator consensus (agreement, else Fable).
Also writes the registered-procedure links (final_links_registered.csv) for the sensitivity analysis."""
import json, pandas as pd
P=pd.read_csv('link_persons.csv'); key=pd.read_csv('items/item_key.csv')
C=pd.concat([pd.read_csv(f'combined_{p}.csv') for p in ('acad','grant','auto')])
fb={}
import os
for f in ('out_tiebreak/fable_tiebreak_all.jsonl','out_tiebreak/fable_tiebreak_auto.jsonl'):
    if not os.path.exists(f): continue
    L=[l for l in open(f) if l.strip()]; assert json.loads(L[0])['model_id']=='claude-fable-5-1'
    for l in L[1:]: x=json.loads(l); fb[x['id']]=x
dis=set(C[~C.agree].item_id)
# Deviation 2026-10-26: Fable unavailable (spend limit) for the 34 disagreements on the extra auto-match check (U items).
# Conservative rule: an unresolved disagreement = not linked (as 'uncertain' in the instructions); sensitivity: linked.
unres=sorted(dis-set(fb)); assert all(i.startswith('U') for i in unres), unres[:5]
for i in unres: fb[i]={'decision':'uncertain','candidate':None,'unresolved':True}
json.dump(unres, open('unresolved_disagreements.json','w'))
def final(r):
    if r.agree: return (r.agreed_link if pd.notna(r.agreed_link) else None), False
    x=fb[r.item_id]; return (x['candidate'] if x['decision']=='match' else None), True
C[['final_cand','contested']]=C.apply(lambda r: pd.Series(final(r)),axis=1)
C['person_id']=C.item_id.map(key.drop_duplicates('item_id').set_index('item_id').person_id)
k=key.set_index(['item_id','candidate']).stanford_row
C['final_row']=[k.get((i,int(c))) if pd.notna(c) else None for i,c in zip(C.item_id,C.final_cand)]
adj=C.set_index('person_id')
F=P[['person_id','source','link_class','auto_stanford_row']].copy()
F['stanford_row']=[adj.at[p,'final_row'] if p in adj.index else None for p in F.person_id]
F['contested']=[bool(adj.at[p,'contested']) if p in adj.index else False for p in F.person_id]
F['linked']=F.stanford_row.notna()
nocand=~F.person_id.isin(adj.index)
assert (F[nocand].link_class=='non-match').all() and int(nocand.sum())==173, 'only the 173 no-candidate non-matches may lack a key'
F.to_csv('final_links.csv',index=False)
# registered procedure: auto-matches kept unless in the 200 sample
reg=F.copy(); samp=set(C[C.item_id.str.startswith('A')].person_id)
m=(reg.link_class=='auto-match')&~reg.person_id.isin(samp)
reg.loc[m,'stanford_row']=reg.loc[m,'auto_stanford_row']; reg.loc[m,'contested']=False; reg['linked']=reg.stanford_row.notna()
reg.to_csv('final_links_registered.csv',index=False)
t=F.groupby('source').agg(people=('person_id','size'),linked=('linked','sum')).join(reg.groupby('source').linked.sum().rename('linked_registered'))
print(t.to_string()); print('linked', int(F.linked.sum()), 'registered', int(reg.linked.sum()), 'contested', int((F.contested&F.linked).sum()))
