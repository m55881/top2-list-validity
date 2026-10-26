"""Final person-to-Stanford links (protocol Section 6).
auto-match: algorithm link kept, except sampled auto-matches, which take the adjudicated consensus.
review / non-match: linked only if the adjudicator consensus is 'match' (agreement, else Fable tie-break).
contested = link decided by the tie-breaker."""
import json, pandas as pd
P=pd.read_csv('link_persons.csv'); key=pd.read_csv('items/item_key.csv')
C=pd.concat([pd.read_csv('combined_acad.csv'),pd.read_csv('combined_grant.csv')])
fb={}
L=[l for l in open('out_tiebreak/fable_tiebreak_all.jsonl') if l.strip()]
assert json.loads(L[0])['model_id']=='claude-fable-5-1'
for l in L[1:]: x=json.loads(l); fb[x['id']]=x
dis=set(C[~C.agree].item_id); assert dis==set(fb), (len(dis),len(fb), dis^set(fb))
def final(r):
    if r.agree: return (r.agreed_link if pd.notna(r.agreed_link) else None), False
    x=fb[r.item_id]; return (x['candidate'] if x['decision']=='match' else None), True
C[['final_cand','contested']]=C.apply(lambda r: pd.Series(final(r)),axis=1)
item_person=key.drop_duplicates('item_id').set_index('item_id').person_id
C['person_id']=C.item_id.map(item_person)
k=key.set_index(['item_id','candidate']).stanford_row
C['final_row']=[k.get((i,int(c))) if pd.notna(c) else None for i,c in zip(C.item_id,C.final_cand)]
F=P[['person_id','source','link_class','auto_stanford_row']].copy()
adj=C.set_index('person_id')
F['adjudicated']=F.person_id.isin(adj.index)
F['stanford_row']=[ (adj.at[p,'final_row'] if p in adj.index else (r if c=='auto-match' else None)) for p,c,r in zip(F.person_id,F.link_class,F.auto_stanford_row)]
F['contested']=[bool(adj.at[p,'contested']) if p in adj.index else False for p in F.person_id]
F['linked']=F.stanford_row.notna()
F.to_csv('final_links.csv',index=False)
flow=F.groupby(['source','link_class']).agg(n=('person_id','size'),linked=('linked','sum')).reset_index()
print(flow.pivot(index='source',columns='link_class',values=['n','linked']).fillna(0).astype(int).to_string())
print('linked total', int(F.linked.sum()), 'contested links', int((F.contested&F.linked).sum()))
s=C[C.item_id.str.startswith('A')]
print('auto-match sample confirmed', int(s.final_row.notna().sum()), 'of', len(s))
print('tiebreak decisions', pd.Series([x['decision'] for x in fb.values()]).value_counts().to_dict())
json.dump({'tiebreak_n':len(fb)}, open('finalize_meta.json','w'))
