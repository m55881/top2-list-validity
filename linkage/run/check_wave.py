import json, sys, glob, os
for b in sys.argv[1:]:
    for m in ('opus','sonnet'):
        f=f'out/{m}_grant_N_b{b}.jsonl'
        if not os.path.exists(f): print(b,m,'MISSING'); continue
        S=[json.loads(l) for l in list(open(f))[1:] if l.strip()]
        u=len(set(x['reason'] for x in S))/len(S)
        if u<0.8: print(b,m,'TEMPLATED',round(u,2))
print('checked')
