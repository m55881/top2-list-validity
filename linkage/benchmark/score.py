import json, base64, gzip, sys, math, random
import numpy as np
def load(p):
    L=[json.loads(l) for l in open(p) if l.strip()]
    mid=L[0].get('model_id'); return mid,{x['id']:x for x in L[1:]}
truth={t['id']:t for t in json.loads(gzip.decompress(base64.b64decode(open('sealed_truth.b64','rb').read())))}
res={}
for m in ['opus','sonnet']:
    a=load(f'out_{m}_batch1.jsonl'); b=load(f'out_{m}_batch2.jsonl')
    res[m]={**a[1],**b[1]}; print(m,'model ids:',a[0],b[0],'n answers:',len(res[m]))
# spot checks against returned text
chk={('opus','B061'):'uncertain',('opus','B101'):'uncertain',('opus','B239'):'uncertain',('sonnet','B007'):'uncertain',('sonnet','B080'):'uncertain',('sonnet','B240'):'uncertain',('sonnet','B373'):'uncertain',('opus','B298'):'non-match'}
print('spot checks ok:', all(res[m][i]['decision']==v for (m,i),v in chk.items()))
def wilson(k,n,z=1.96):
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return c-h,c+h
ids=sorted(truth)
def linked(m,i): return res[m].get(i,{}).get('decision')=='match'
def kappa(a,b):
    cats=sorted(set(a)|set(b)); n=len(a)
    po=sum(x==y for x,y in zip(a,b))/n
    pe=sum((a.count(c)/n)*(b.count(c)/n) for c in cats); return (po-pe)/(1-pe)
out={}
for m in ['opus','sonnet']:
    tp=sum(linked(m,i) for i in ids if truth[i]['label']=='match')
    tn=sum(not linked(m,i) for i in ids if truth[i]['label']=='non-match')
    unc=sum(res[m][i]['decision']=='uncertain' for i in ids)
    se,sp=tp/200,tn/200
    out[m]=dict(sens=se,sens_ci=wilson(tp,200),spec=sp,spec_ci=wilson(tn,200),uncertain=unc,accepted=se>=.95 and sp>=.95)
    print(m, out[m])
a3=[res['opus'][i]['decision'] for i in ids]; b3=[res['sonnet'][i]['decision'] for i in ids]
a2=['L' if x=='match' else 'N' for x in a3]; b2=['L' if x=='match' else 'N' for x in b3]
rng=random.Random(20261012); ks=[]
for _ in range(2000):
    s=[rng.randrange(400) for _ in range(400)]
    ks.append(kappa([a2[j] for j in s],[b2[j] for j in s]))
print('kappa 3-cat', round(kappa(a3,b3),3), ' kappa linked', round(kappa(a2,b2),3), 'CI', np.percentile(ks,[2.5,97.5]).round(3))
dis=[i for i in ids if a2[ids.index(i)]!=b2[ids.index(i)]]
print('disagreements (linked vs not):', len(dis), dis)
json.dump(dis,open('disagreements.json','w'))
# errors detail
for m in ['opus','sonnet']:
    for i in ids:
        t=truth[i]; L=linked(m,i)
        if (t['label']=='match')!=L: print(m,i,t['label'],t['inst_variant'],t['name_variant'],res[m][i]['decision'],'|',res[m][i]['reason'])
