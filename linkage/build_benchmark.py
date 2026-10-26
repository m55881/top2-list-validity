"""Build the 400-pair synthetic linkage benchmark (protocol Section 6) from the
Stanford-Elsevier Version 2 career-long table only. No criterion data are used.

200 true matches: a listed scientist's record altered the way election and grant
lists differ from it (initials only, missing middle names, accents removed, nickname,
a related or reformatted institution, a later institution, country only).
200 true non-matches: two different listed scientists sharing a normalized family
name and first initial (half with an identical first given name).

Output: benchmark_items.json (what adjudicators see) and sealed_truth.b64 (answers,
gzip+base64, not shown to adjudicators).
"""
import base64, gzip, hashlib, json, random, re, sys
import pandas as pd
import pycountry

sys.path.insert(0, './linkage')
from normalize import split_stanford, family_keys, given_info, ascii_fold, distinctive_tokens as inst_tokens

SEED = 20261012
rng = random.Random(SEED)
OUT = './linkage/benchmark/'
HEALTH = {'Clinical Medicine', 'Biomedical Research', 'Public Health & Health Services'}

d = pd.read_parquet('data/stanford/v2_career.parquet')
d = d[d['sm-field'].astype(str).str.strip() != ''].reset_index(drop=True)
d['row'] = d.index
fam_giv = d.authfull.map(split_stanford)
d['family'] = fam_giv.map(lambda x: x[0])
d['given'] = fam_giv.map(lambda x: x[1])
d['gfirst'] = d.given.map(lambda g: given_info(g)['first'])
d['ginit'] = d.gfirst.str[:1]
d['fkey'] = d.family.map(lambda f: ''.join(c for c in ascii_fold(f) if c.isalpha()))
d['health'] = d['sm-field'].isin(HEALTH)


def cname(code):
    try:
        c = pycountry.countries.get(alpha_3=str(code).upper())
        return getattr(c, 'common_name', None) or c.name
    except Exception:
        return str(code).upper()


NICK = {'william': 'Bill', 'robert': 'Bob', 'richard': 'Rick', 'michael': 'Mike', 'james': 'Jim',
        'elizabeth': 'Liz', 'katherine': 'Kate', 'catherine': 'Cathy', 'thomas': 'Tom',
        'joseph': 'Joe', 'stephen': 'Steve', 'steven': 'Steve', 'daniel': 'Dan', 'david': 'Dave',
        'christopher': 'Chris', 'jennifer': 'Jenny', 'margaret': 'Maggie', 'edward': 'Ed',
        'andrew': 'Andy', 'anthony': 'Tony', 'patricia': 'Pat', 'nicholas': 'Nick',
        'jonathan': 'Jon', 'benjamin': 'Ben', 'samuel': 'Sam', 'timothy': 'Tim', 'peter': 'Pete'}


def strip_accents_keep_case(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def name_variant(family, given, kind):
    gtoks = [t for t in re.split(r'\s+', given.strip()) if t]
    first = gtoks[0] if gtoks else ''
    if kind == 'initial_only':
        g = first[:1] + '.'
    elif kind == 'drop_middle':
        g = first
    elif kind == 'nickname' and ascii_fold(first) in NICK:
        g = NICK[ascii_fold(first)]
    elif kind == 'expand_none':
        g = given
    else:
        g = given
    fam = family
    if kind == 'hyphen_part' and '-' in family:
        fam = family.split('-')[0]
    if kind == 'drop_particle':
        toks = family.split()
        if len(toks) > 1 and ascii_fold(toks[0]) in {'van', 'von', 'de', 'der', 'di', 'da', 'del', 'la', 'le'}:
            fam = ' '.join(toks[1:])
    name = f'{g} {fam}'.strip()
    if rng.random() < 0.5:
        name = strip_accents_keep_case(name)
    return name


# institutions indexed by distinctive token for "related institution" variants
inst_by_tok = {}
for inst, c in d[['inst_name', 'cntry']].drop_duplicates().itertuples(index=False):
    for t in inst_tokens(inst):
        inst_by_tok.setdefault((t, c), set()).add(inst)
insts_by_country = d.groupby('cntry').inst_name.unique().to_dict()


def reformat_inst(inst):
    s = inst
    for a, b in [('University of ', 'Univ. of '), ('University', 'Univ.'), ('Institute', 'Inst.'),
                 ('The ', ''), (' and ', ' & '), ('Hospital', 'Hosp.'), ('Medical Center', 'Med. Ctr.')]:
        if a in s:
            return s.replace(a, b, 1)
    return s + ' (main campus)'


def inst_variant(row, kind):
    inst, c = row.inst_name, row.cntry
    if kind == 'exact':
        return inst, 'exact'
    if kind == 'reformat':
        return reformat_inst(inst), 'reformat'
    if kind == 'related':
        cands = set()
        for t in inst_tokens(inst):
            cands |= inst_by_tok.get((t, c), set())
        cands.discard(inst)
        if cands:
            return rng.choice(sorted(cands)), 'related'
        return reformat_inst(inst), 'reformat'
    if kind == 'moved':
        pool = [i for i in insts_by_country.get(c, []) if i != inst]
        if pool:
            return rng.choice(pool), 'moved'
        return inst, 'exact'
    if kind == 'country_only':
        return '', 'country_only'
    raise ValueError(kind)


def field_hint(row):
    r = rng.random()
    if r < 0.4:
        return row['sm-subfield-1']
    if r < 0.7:
        return row['sm-field']
    return ''


def source_type():
    return rng.choice(['academy election, 2020-2025', 'research grant award (lead investigator), 2020-2025'])


def criterion_record(row, name_kind, inst_kind):
    name = name_variant(row.family, row.given, name_kind)
    inst, ik = inst_variant(row, inst_kind)
    fh = field_hint(row)
    if ik in ('moved', 'country_only') and not fh:
        # weak institution evidence always comes with a field hint, as in real lists
        fh = row['sm-subfield-1'] if rng.random() < 0.5 else row['sm-field']
    return {'name': name, 'institution': inst, 'country': cname(row.cntry),
            'field_or_section': fh, 'source': source_type()}, ik


def stanford_record(row):
    return {'name': row.authfull, 'institution': row.inst_name, 'country': cname(row.cntry),
            'main_field': row['sm-field'], 'main_subfield': row['sm-subfield-1'],
            'publication_years': f'{int(row.firstyr)}-{int(row.lastyr)}'}


def pick_population(n):
    nh = round(n * 0.75)
    return pd.concat([d[d.health].sample(nh, random_state=rng.randrange(10**9)),
                      d[~d.health].sample(n - nh, random_state=rng.randrange(10**9))])


# name / institution difficulty mix (applied to the criterion side of every pair)
NAME_KINDS = (['expand_none'] * 30 + ['drop_middle'] * 35 + ['initial_only'] * 10 + ['nickname'] * 10 +
              ['hyphen_part'] * 8 + ['drop_particle'] * 7)
INST_KINDS = ['exact'] * 20 + ['reformat'] * 20 + ['related'] * 35 + ['moved'] * 10 + ['country_only'] * 15


def draw_kinds(row):
    nk = rng.choice(NAME_KINDS)
    if nk == 'nickname' and ascii_fold(row.gfirst) not in NICK:
        nk = 'drop_middle'
    if nk == 'hyphen_part' and '-' not in row.family:
        nk = 'expand_none'
    if nk == 'drop_particle' and len(row.family.split()) < 2:
        nk = 'drop_middle'
    ik = rng.choice(INST_KINDS)
    # keep every true match decidable in principle: an initial-only name always comes
    # with institution evidence, and a country-only record always with a full given name
    if nk == 'initial_only' and ik in ('country_only', 'moved'):
        ik = rng.choice(['exact', 'reformat', 'related'])
    return nk, ik


items, truth = [], []

# ---- 200 true matches
used = set()
pop = pick_population(400).sample(frac=1, random_state=SEED)
for _, row in pop.iterrows():
    if len([t for t in truth if t['label'] == 'match']) >= 200:
        break
    if not row.gfirst or len(row.gfirst) < 2 or row.row in used:
        continue
    used.add(row.row)
    nk, ik = draw_kinds(row)
    crit, ik2 = criterion_record(row, nk, ik)
    items.append({'criterion_record': crit, 'stanford_record': stanford_record(row)})
    truth.append({'label': 'match', 'name_variant': nk, 'inst_variant': ik2,
                  'crit_row': int(row.row), 'stanford_row': int(row.row), 'health': bool(row.health)})

# ---- 200 true non-matches: same family key and first initial, different person
groups = d[d.gfirst.str.len() >= 2].groupby(['fkey', 'ginit']).row.apply(list)
groups = groups[groups.map(len) >= 2]
pairs_same_first, pairs_diff_first = [], []
for rows in groups:
    sub = d.loc[rows]
    for i in range(len(rows)):
        for j in range(i + 1, min(len(rows), i + 6)):
            a, b = sub.iloc[i], sub.iloc[j]
            if a.inst_name == b.inst_name:
                continue
            same_first = ascii_fold(a.gfirst) == ascii_fold(b.gfirst)
            # exclude possible split profiles of one person
            if same_first and a.cntry == b.cntry and a['sm-subfield-1'] == b['sm-subfield-1']:
                continue
            if inst_tokens(a.inst_name) & inst_tokens(b.inst_name) and a['sm-subfield-1'] == b['sm-subfield-1']:
                continue
            (pairs_same_first if same_first else pairs_diff_first).append((a.row, b.row))
rng.shuffle(pairs_same_first)
rng.shuffle(pairs_diff_first)


def take(pairs, n, health_share=0.75):
    out, seen = [], set()
    nh = round(n * health_share)
    for want_health in (True, False):
        quota = nh if want_health else n - nh
        for a, b in pairs:
            if quota == 0:
                break
            if a in seen or b in seen or a in used or b in used:
                continue
            if bool(d.at[a, 'health']) != want_health:
                continue
            out.append((a, b)); seen |= {a, b}; quota -= 1
    return out


# at least 60% of non-match pairs share a country (harder, and closer to real lists)
def split_country(pairs):
    same = [p for p in pairs if d.at[p[0], 'cntry'] == d.at[p[1], 'cntry']]
    diff = [p for p in pairs if d.at[p[0], 'cntry'] != d.at[p[1], 'cntry']]
    return same, diff


neg = []
for pool in (pairs_same_first, pairs_diff_first):
    same_c, diff_c = split_country(pool)
    part = take(same_c, 60)
    used |= {x for p in part for x in p}
    part += take(diff_c, 40)
    used |= {x for p in part for x in p}
    neg += part
for a, b in neg:
    ra, rb = d.loc[a], d.loc[b]
    nk, ik = draw_kinds(ra)
    crit, ik2 = criterion_record(ra, nk, ik)
    # a displayed "related"/"moved" institution must not accidentally point to b's institution
    if crit['institution'] and inst_tokens(crit['institution']) & inst_tokens(rb.inst_name) and ik2 in ('related', 'moved'):
        crit['institution'] = ra.inst_name; ik2 = 'exact'
    items.append({'criterion_record': crit, 'stanford_record': stanford_record(rb)})
    truth.append({'label': 'non-match', 'name_variant': nk, 'inst_variant': ik2,
                  'same_first_name': ascii_fold(ra.gfirst) == ascii_fold(rb.gfirst),
                  'crit_row': int(a), 'stanford_row': int(b), 'health': bool(ra.health)})

assert sum(t['label'] == 'match' for t in truth) == 200, sum(t['label'] == 'match' for t in truth)
assert sum(t['label'] == 'non-match' for t in truth) == 200, sum(t['label'] == 'non-match' for t in truth)

order = list(range(400)); rng.shuffle(order)
items = [items[i] for i in order]; truth = [truth[i] for i in order]
for k, (it, tr) in enumerate(zip(items, truth), 1):
    it['id'] = tr['id'] = f'B{k:03d}'
items = [{'id': it['id'], 'criterion_record': it['criterion_record'], 'stanford_record': it['stanford_record']} for it in items]

import os
os.makedirs(OUT, exist_ok=True)
ib = json.dumps(items, ensure_ascii=False, indent=1).encode()
open(OUT + 'benchmark_items.json', 'wb').write(ib)
tb = json.dumps(truth, ensure_ascii=False).encode()
open(OUT + 'sealed_truth.b64', 'wb').write(base64.b64encode(gzip.compress(tb)))
meta = {'seed': SEED, 'n_items': 400, 'sha256_items': hashlib.sha256(ib).hexdigest(),
        'sha256_truth_json': hashlib.sha256(tb).hexdigest(), 'built_utc': pd.Timestamp.now('UTC').isoformat()}
json.dump(meta, open(OUT + 'benchmark_meta.json', 'w'), indent=1)
t = pd.DataFrame(truth)
print(t.groupby(['label', 'inst_variant']).size().unstack(fill_value=0))
print(t.groupby(['label', 'name_variant']).size().unstack(fill_value=0))
print('same first name among non-matches:', t.same_first_name.sum(), ' health share:', t.health.mean())
print('non-match same country:', sum(it['criterion_record']['country']==it['stanford_record']['country'] for it,tr in zip(items,truth) if tr['label']=='non-match'))
print(meta)
