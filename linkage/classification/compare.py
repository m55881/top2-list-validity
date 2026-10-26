import json
def load(p):
    L=[json.loads(l) for l in open(p) if l.strip()]
    return L[0].get('model_id'), {x['id']:x for x in L[1:]}
E={};W={};mids=set()
for m in ['opus','sonnet']:
    E[m]={}
    for b in (1,2,3):
        mid,d=load(f'out_{m}_electees_batch{b}.jsonl'); mids.add((m,mid)); E[m].update(d)
    mid,W[m]=load(f'out_{m}_wellcome.jsonl'); mids.add((m,mid))
print(sorted(mids))
ids=[json.loads(l)['id'] for b in (1,2,3) for l in open(f'electees_batch{b}.jsonl')]
print('electee answers', {m:len(E[m]) for m in E}, 'missing', {m:[i for i in ids if i not in E[m]][:5] for m in E})
from collections import Counter
for m in E: print(m, Counter(E[m][i]['classification'] for i in ids))
dis=[i for i in ids if E['opus'][i]['classification']!=E['sonnet'][i]['classification']]
po=1-len(dis)/len(ids)
ca=Counter(E['opus'][i]['classification'] for i in ids); cb=Counter(E['sonnet'][i]['classification'] for i in ids)
pe=sum(ca[k]*cb[k] for k in ca)/len(ids)**2
print('electee disagreements',len(dis),'kappa',round((po-pe)/(1-pe),3))
for m in W: print(m,{k:v['health_related'] for k,v in W[m].items()})
wdis=[k for k in W['opus'] if W['opus'][k]['health_related']!=W['sonnet'][k]['health_related']]
print('wellcome disagreements',wdis)
items={json.loads(l)['id']:json.loads(l) for b in (1,2,3) for l in open(f'electees_batch{b}.jsonl')}
witems={json.loads(l)['id']:json.loads(l) for l in open('wellcome_hss_items.jsonl')}
with open('tiebreak_classification_items.jsonl','w') as f:
    for i in dis:
        x=dict(items[i]); x['task']='A'; x['classifier_A']={k:E['opus'][i][k] for k in ('classification','reason')}; x['classifier_B']={k:E['sonnet'][i][k] for k in ('classification','reason')}
        f.write(json.dumps(x,ensure_ascii=False)+'\n')
    for i in wdis:
        x=dict(witems[i]); x['task']='B'; x['classifier_A']={k:W['opus'][i][k] for k in ('health_related','reason')}; x['classifier_B']={k:W['sonnet'][i][k] for k in ('health_related','reason')}
        f.write(json.dumps(x,ensure_ascii=False)+'\n')
for i in dis[:40]: print(i, items[i]['name'],'|',items[i]['election_text'][:90],'| A:',E['opus'][i]['classification'],'B:',E['sonnet'][i]['classification'])
