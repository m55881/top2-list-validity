import json, os
m=json.load(open('items/manifest.json')); out=set(os.listdir('out'))
todo=[(md,x[0][:-4]) for x in m for md in ('opus','sonnet') if f'{md}_{x[0][:-4]}.jsonl' not in out]
print(len(todo)); print(' '.join(f'{a}:{b}' for a,b in todo[:12]))
