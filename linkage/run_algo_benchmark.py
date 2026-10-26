"""Run the linkage algorithm on the 400 benchmark criterion records against the full Stanford v2 table."""
import sys, json, base64, gzip; sys.path.insert(0, './linkage')
import pandas as pd
from link import StanfordIndex, link
from normalize import split_natural
d = pd.read_parquet('data/stanford/v2_career.parquet')
d = d[d['sm-field'].astype(str).str.strip() != ''].reset_index(drop=True)
idx = StanfordIndex(d)
items = json.load(open('benchmark/benchmark_items.json'))
truth = {t['id']: t for t in json.loads(gzip.decompress(base64.b64decode(open('benchmark/sealed_truth.b64', 'rb').read())))}
rows = []
for it in items:
    c = it['criterion_record']; fam, giv = split_natural(c['name'])
    rows.append(dict(person_id=it['id'], source='benchmark', year=2020, family=fam, given=giv,
                     affiliation=c['institution'], country=c['country'], field_hint=c['field_or_section']))
P, Q = link(pd.DataFrame(rows), idx)
P['label'] = P.person_id.map(lambda i: truth[i]['label'])
P['source_person_row'] = P.person_id.map(lambda i: truth[i]['crit_row'])
P['source_person_found'] = [((Q.person_id == p) & (Q.stanford_row == t)).any() for p, t in zip(P.person_id, P.source_person_row)]
am = P[P.link_class == 'auto-match']
res = {'class_by_label': pd.crosstab(P.label, P.link_class).to_dict(),
       'source_person_among_candidates': float(P.source_person_found.mean()),
       'auto_matches': int(len(am)), 'auto_match_correct_person': float((am.auto_stanford_row == am.source_person_row).mean()),
       'mean_candidates': float(P.n_candidates.mean())}
print(json.dumps(res, indent=1))
json.dump(res, open('benchmark/algorithm_on_benchmark.json', 'w'), indent=1)
print(P[~P.source_person_found].person_id.tolist())
