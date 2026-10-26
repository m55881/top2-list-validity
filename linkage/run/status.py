import json, os, glob
m=[x[0][:-4] for x in json.load(open('./linkage/run/items/manifest.json'))]
done={}
for f in glob.glob('./linkage/run/out/*.jsonl'):
    b=os.path.basename(f)[:-6]; mod,stem=b.split('_',1); done.setdefault(stem,set()).add(mod)
g=[s for s in m if s.startswith('grant')]
both=[s for s in g if done.get(s)=={'opus','sonnet'}]; one=[(s,done[s]) for s in g if s in done and len(done[s])==1]; none=[s for s in g if s not in done]
print('grant complete',len(both),'/',len(g),'| partial',one,'| next',none[:6])
