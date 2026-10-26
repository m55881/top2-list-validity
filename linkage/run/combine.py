"""Combine Opus and Sonnet decisions per item; list disagreements for the Fable tie-break."""
import json, glob, os, sys, re
import pandas as pd
OUT='./linkage/run/out/'; IT='./linkage/run/items/'
prefix=sys.argv[1]  # e.g. acad or grant
def load(model):
    d={}
    for f in sorted(glob.glob(f'{OUT}{model}_{prefix}_*.jsonl')):
        for l in list(open(f))[1:]:
            if l.strip(): x=json.loads(l); d[x['id']]=x
    return d
A,B=load('opus'),load('sonnet')
ids=sorted(set(A)&set(B))
def lab(x): return ('match',x.get('candidate')) if x['decision']=='match' else ('no',None)
rows=[]
for i in ids:
    a,b=lab(A[i]),lab(B[i])
    rows.append(dict(item_id=i,opus=A[i]['decision'],opus_cand=A[i].get('candidate'),sonnet=B[i]['decision'],sonnet_cand=B[i].get('candidate'),agree=a==b,
                     agreed_link=a[1] if a==b and a[0]=='match' else None))
R=pd.DataFrame(rows); R.to_csv(f'./linkage/run/combined_{prefix}.csv',index=False)
kind=R.item_id.str[0]
print('items',len(R),'only one model:',len(set(A)^set(B)))
print(pd.crosstab(kind,R.agree))
la=(R.opus=='match'); lb=(R.sonnet=='match'); po=((la==lb)).mean(); pe=la.mean()*lb.mean()+(1-la.mean())*(1-lb.mean())
print('kappa linked/not', round((po-pe)/(1-pe),3))
print('links agreed by kind', R[R.agreed_link.notna()].item_id.str[0].value_counts().to_dict())
# tie-break file
blocks={}
for f in glob.glob(f'{IT}{prefix}_*.txt'):
    cur=None
    for l in open(f):
        if l.startswith('### '): cur=l[4:].strip(); blocks[cur]=l
        elif cur: blocks[cur]+=l
dis=R[~R.agree]
with open(f'./linkage/run/items/tiebreak_{prefix}.txt','w') as f:
    for r in dis.itertuples():
        f.write(blocks[r.item_id])
        f.write(f"  ADJUDICATOR A: {A[r.item_id]['decision']} candidate={A[r.item_id].get('candidate')} | {A[r.item_id]['reason']}\n")
        f.write(f"  ADJUDICATOR B: {B[r.item_id]['decision']} candidate={B[r.item_id].get('candidate')} | {B[r.item_id]['reason']}\n")
print('disagreements', len(dis))
