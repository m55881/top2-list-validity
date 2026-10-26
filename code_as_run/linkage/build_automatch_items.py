"""Deviation (2026-10-26, after the registered 200-match sample gave precision 0.93): every remaining
auto-match is adjudicated by the same two models with the same instructions. Items 'U'."""
import sys, json; sys.path.insert(0,'/home/claude/linkage')
import pandas as pd
exec(open('/home/claude/linkage/build_adjudication_items.py').read().split("items, key = ")[0])  # helpers: d, ppl, cand_text, crit, OUT
P=pd.read_csv('/home/claude/linkage/run/link_persons.csv'); key=pd.read_csv(OUT+'item_key.csv')
sampled=set(key[key.item_id.str.startswith('A')].person_id)
am=P[(P.link_class=='auto-match')&~P.person_id.isin(sampled)].sample(frac=1,random_state=20261026)
newkey=[]; blocks=[]
for n,r in enumerate(am.itertuples(index=False),1):
    iid=f'U{n:05d}'; row=int(r.auto_stanford_row)
    newkey.append((iid,r.person_id,r.source,1,row))
    c=crit(r.person_id)
    blocks.append(f"### {iid}\nCRITERION: "+" | ".join(f"{k}: {v}" for k,v in c.items() if v)+f"\n  1) {cand_text(row)}\n")
pd.concat([key,pd.DataFrame(newkey,columns=key.columns)]).to_csv(OUT+'item_key.csv',index=False)
man=[]
for b in range(0,len(blocks),250):
    name=f'auto_U_b{b//250+1:03d}.txt'; open(OUT+name,'w').write(''.join(blocks[b:b+250])); man.append((name,len(blocks[b:b+250])))
json.dump(man,open(OUT+'manifest_auto.json','w'))
print(len(blocks),'items',len(man),'batches')
