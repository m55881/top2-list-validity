"""Flag outputs whose reasons look templated (share of distinct reasons < 0.6) and validate counts."""
import json, glob, sys, collections, subprocess
pat=sys.argv[1] if len(sys.argv)>1 else '*'
for f in sorted(glob.glob(f'out/{pat}.jsonl')):
    L=[json.loads(l) for l in list(open(f))[1:] if l.strip()]
    r=[x.get('reason','') for x in L]; u=len(set(r))/max(1,len(r))
    if u<0.6: print('LOW-UNIQUE', f, len(L), round(u,2), collections.Counter(r).most_common(1)[0][1])
