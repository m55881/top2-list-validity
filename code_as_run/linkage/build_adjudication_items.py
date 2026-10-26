"""Build adjudication item files for the real linkage run (protocol Section 6):
  R: every 'review' person, with all non-conflicting candidates from blocking
  N: every 'non-match' person, with the 10 most similar Stanford names
  A: a random sample of 200 auto-matches (seed 20261014), with the auto-matched record
Items are written one per line in a compact text-friendly JSON so that long candidate lists stay readable.
A key file maps (item id, candidate number) -> Stanford row."""
import sys, json, random, os
sys.path.insert(0, '/home/claude/linkage')
import pandas as pd
import pycountry

import sys as _s
OUT = _s.argv[1] if len(_s.argv) > 1 else '/home/claude/linkage/run/items/'
os.makedirs(OUT, exist_ok=True)
d = pd.read_parquet('/home/claude/data/v2_career.parquet').reset_index(drop=True)
P = pd.read_csv('/home/claude/linkage/run/link_persons.csv')
Q = pd.read_csv('/home/claude/linkage/run/link_pairs.csv')
ppl = pd.read_csv('/home/claude/data/derived/criterion_people.csv', keep_default_na=False).set_index('person_id')
NM = pd.read_json('/home/claude/linkage/run/nonmatch_top10.json').set_index('person_id')
SRC = {'NAM': 'US National Academy of Medicine election', 'AMS': 'UK Academy of Medical Sciences election',
       'NAS': 'US National Academy of Sciences election', 'RoyalSociety': 'Royal Society election',
       'TWAS': 'The World Academy of Sciences election', 'NIH_R01': 'NIH R01 grant (contact PI)',
       'MRC': 'UK MRC research grant (PI)', 'Wellcome': 'Wellcome award (lead applicant)',
       'CIHR': 'CIHR Project Grant (nominated principal applicant)', 'KAKEN': 'JSPS KAKENHI (S)/(A) grant (PI)',
       'NHMRC': 'NHMRC Investigator Grant (chief investigator)', 'ERC_LS': 'ERC Advanced/Consolidator grant, life sciences (PI)'}


def cname(c):
    c = str(c or '').strip()
    if not c:
        return ''
    try:
        x = pycountry.countries.get(alpha_3=c.upper())
        return getattr(x, 'common_name', None) or x.name
    except Exception:
        return c.upper()


def cand_text(i):
    s = d.loc[i]
    yrs = f"{int(s.firstyr)}-{int(s.lastyr)}" if pd.notna(s.firstyr) else ''
    return f"{s.authfull} | {s.inst_name} | {cname(s.cntry)} | {s['sm-field']} / {s['sm-subfield-1']} | {yrs}"


def crit(pid):
    r = ppl.loc[pid]
    aff = str(r.affiliation)[:220]
    rec = {'name': f'{r.given} {r.family}'.strip(), 'institution': aff, 'country': cname(r.country),
           'source': f"{SRC.get(r.source, r.source)}, first in {r.first_year}"}
    if r.field_hint:
        rec['field_or_section'] = r.field_hint
    return rec


items, key = {'R': [], 'N': [], 'A': []}, []
item_person = []
order = {'NAM': 0, 'AMS': 1, 'NAS': 2, 'RoyalSociety': 3, 'TWAS': 4, 'Wellcome': 5, 'MRC': 6, 'CIHR': 7,
         'KAKEN': 8, 'NHMRC': 9, 'ERC_LS': 10, 'NIH_R01': 11}
rng = random.Random(20261014)

rev = P[P.link_class == 'review'].copy()
rev['o'] = rev.source.map(order)
for kind, sub in [('R', rev), ('N', P[P.link_class == 'non-match'].assign(o=lambda x: x.source.map(order)))]:
    sub = sub.sample(frac=1, random_state=20261014).sort_values('o', kind='stable')
    for n, r in enumerate(sub.itertuples(index=False), 1):
        iid = f'{kind}{n:05d}'
        if kind == 'R':
            rows = Q[Q.person_id == r.person_id].stanford_row.tolist()
        else:
            rows = NM.loc[r.person_id, 'top10']
        cands = {str(k): cand_text(i) for k, i in enumerate(rows, 1)}
        for k, i in enumerate(rows, 1):
            key.append((iid, r.person_id, r.source, k, int(i)))
        item_person.append((iid, r.person_id, r.source)); items[kind].append({'id': iid, 'source_group': r.source, 'criterion_record': crit(r.person_id), 'candidates': cands})

am = P[P.link_class == 'auto-match'].sample(200, random_state=20261014)
for n, r in enumerate(am.itertuples(index=False), 1):
    iid = f'A{n:05d}'
    key.append((iid, r.person_id, r.source, 1, int(r.auto_stanford_row)))
    item_person.append((iid, r.person_id, r.source)); items['A'].append({'id': iid, 'source_group': r.source, 'criterion_record': crit(r.person_id),
                       'candidates': {'1': cand_text(int(r.auto_stanford_row))}})

pd.DataFrame(item_person, columns=['item_id', 'person_id', 'source']).to_csv(OUT + 'item_persons.csv', index=False)
pd.DataFrame(key, columns=['item_id', 'person_id', 'source', 'candidate', 'stanford_row']).to_csv(OUT + 'item_key.csv', index=False)
ACAD = {'NAM', 'AMS', 'NAS', 'RoyalSociety', 'TWAS'}


def block(x):
    c = x['criterion_record']
    lines = [f"### {x['id']}",
             "CRITERION: " + " | ".join(f"{k}: {v}" for k, v in c.items() if v)]
    if x['candidates']:
        lines += [f"  {k}) {v}"[:400] for k, v in x['candidates'].items()]
    else:
        lines.append("  (no candidates)")
    return "\n".join(lines) + "\n"


def write_batches(kind, lst, max_chars, max_items, tag):
    bs, cur, n = [], [], 0

    def flush():
        if cur:
            name = f'{tag}_{kind}_b{len(bs) + 1:03d}.txt'
            open(OUT + name, 'w').write(''.join(b for _, b in cur))
            bs.append((name, len(cur), sum(len(b) for _, b in cur)))
    for x in lst:
        b = block(x)
        if cur and (sum(len(y) for _, y in cur) + len(b) > max_chars or len(cur) >= max_items):
            flush(); cur = []
        cur.append((x['id'], b))
    flush()
    return bs


manifest = []
for kind in ('R', 'N', 'A'):
    acad = [x for x in items[kind] if x['source_group'] in ACAD]
    grant = [x for x in items[kind] if x['source_group'] not in ACAD]
    manifest += write_batches(kind, acad, 180000, 250, 'acad') + write_batches(kind, grant, 180000, 250, 'grant')
json.dump(manifest, open(OUT + 'manifest.json', 'w'), indent=0)
print({k: len(v) for k, v in items.items()}, 'batches', len(manifest))
print('acad batches', [m for m in manifest if m[0].startswith('acad')])
print('max batch chars', max(m[2] for m in manifest), 'max line', max(len(l) for m in manifest for l in open(OUT+m[0])))
print('items with no candidates', sum(1 for x in items['N'] if not x['candidates']))
