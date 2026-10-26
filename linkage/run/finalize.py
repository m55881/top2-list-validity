"""Final person-level links for a group (acad | grant):
 - review and non-match items: Opus+Sonnet agreement, else Fable tie-break (flagged contested);
 - auto-matches: kept, except sampled ones that the consensus rejects;
 - uncertain = not linked."""
import json, sys, glob
import pandas as pd
g=sys.argv[1]; R='./linkage/run/'
C=pd.read_csv(f'{R}combined_{g}.csv')
key=pd.read_csv(R+'items/item_key.csv')
P=pd.read_csv(R+'link_persons.csv')
fb={}
for f in glob.glob(f'{R}out/fable_tiebreak_{g}*.jsonl'):
    for l in list(open(f))[1:]:
        if l.strip(): x=json.loads(l); fb[x['id']]=x
dec=[]
for r in C.itertuples():
    if r.agree:
        cand=r.opus_cand if r.opus=='match' else None; contested=False
    else:
        x=fb.get(r.item_id)
        if x is None: cand=None; contested='PENDING'
        else: cand=x.get('candidate') if x['decision']=='match' else None; contested=True
    dec.append((r.item_id, cand, contested))
D=pd.DataFrame(dec,columns=['item_id','cand','contested'])
D=D.merge(key.drop_duplicates('item_id')[['item_id','person_id','source']],on='item_id')
D['stanford_row']=[int(key[(key.item_id==i)&(key.candidate==int(c))].stanford_row.iloc[0]) if pd.notna(c) else None for i,c in zip(D.item_id,D.cand)]
ACAD={'NAM','AMS','NAS','RoyalSociety','TWAS'}
Pg=P[P.source.isin(ACAD)] if g=='acad' else P[~P.source.isin(ACAD)]
out=[]
for p in Pg.itertuples():
    d=D[D.person_id==p.person_id]
    if p.link_class=='auto-match':
        if len(d) and d.stanford_row.isna().all():
            out.append((p.person_id,p.source,None,'auto-rejected-by-adjudicators',bool(d.contested.iloc[0] is True)))
        else:
            out.append((p.person_id,p.source,int(p.auto_stanford_row),'auto-match',False))
    else:
        row=d.stanford_row.iloc[0] if len(d) else None
        out.append((p.person_id,p.source,row,'adjudicated-'+p.link_class,d.contested.iloc[0] if len(d) else False))
F=pd.DataFrame(out,columns=['person_id','source','stanford_row','route','contested'])
F['linked']=F.stanford_row.notna()
F.to_csv(f'{R}final_links_{g}.csv',index=False)
print(F.groupby('source').linked.agg(['sum','count']).assign(pct=lambda x:(x['sum']/x['count']).round(3)).to_string())
print('contested links', int(((F.contested==True)&F.linked).sum()), 'pending', int((F.contested=='PENDING').sum()))
print(F.groupby(['route','linked']).size().to_string())
