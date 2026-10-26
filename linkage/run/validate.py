"""Check every adjudicator output against its batch: model id, item count, ids, valid decisions/candidates."""
import json, re, glob, sys, os
IT='./linkage/run/items/'; OUT='./linkage/run/out/'
def batch_items(stem):
    ids, ncand = [], {}
    cur=None
    for l in open(IT+stem+'.txt'):
        if l.startswith('### '): cur=l[4:].strip(); ids.append(cur); ncand[cur]=0
        elif re.match(r'\s+\d+\) ', l): ncand[cur]+=1
    return ids, ncand
bad=[]; done=[]
for f in sorted(glob.glob(OUT+'*.jsonl')):
    model, stem = os.path.basename(f)[:-6].split('_',1)
    ids, nc = batch_items(stem)
    L=[l for l in open(f) if l.strip()]
    try:
        mid=json.loads(L[0]).get('model_id'); rows=[json.loads(l) for l in L[1:]]
    except Exception as e:
        bad.append((f,'parse',str(e))); continue
    got=[r.get('id') for r in rows]
    probs=[]
    if got!=ids: probs.append(f'ids mismatch: {len(got)} vs {len(ids)}; missing {len(set(ids)-set(got))}')
    for r in rows:
        if r.get('decision') not in ('match','non-match','uncertain'): probs.append(f"bad decision {r.get('id')}")
        if r.get('decision')=='match' and not (isinstance(r.get('candidate'),int) and 1<=r['candidate']<=nc.get(r.get('id'),0)): probs.append(f"bad candidate {r.get('id')} {r.get('candidate')}")
    exp={'opus':'claude-opus-5-5','sonnet':'claude-sonnet-5-5'}.get(model)
    if exp and mid!=exp: probs.append(f'model id {mid}')
    (bad if probs else done).append((os.path.basename(f), probs[:5]) if probs else os.path.basename(f))
print('OK', len(done)); [print('BAD', b) for b in bad]
