import json, glob, os, subprocess
from collections import Counter
print(subprocess.run(['python3','-I','validate.py'],capture_output=True,text=True).stdout.strip().splitlines()[-3:])
bad=[]
for f in sorted(glob.glob('out/*.jsonl')):
    L=[json.loads(l) for l in list(open(f))[1:] if l.strip()]
    top=Counter(x['reason'] for x in L).most_common(1)[0][1]/len(L)
    if top>=0.40: bad.append((os.path.basename(f),round(top,2)))
print('quality flags:',bad)
m=json.load(open('items/manifest.json')); have=set(os.listdir('out'))
miss=sorted({x[0][:-4] for x in m for md in ('opus','sonnet') if f'{md}_{x[0][:-4]}.jsonl' not in have})
print('batches still missing a model:',len(miss), miss[:6], '...')
