"""Record-linkage algorithm (protocol Section 6). Frozen before outcome linkage.

Input: a criterion table with columns
    person_id, source, year, family, given, affiliation, country (name or ISO3), field_hint
and the Stanford-Elsevier table (Version 2 career-long, or any version with authfull, inst_name,
cntry, sm-field, sm-subfield-1, firstyr, lastyr).

Output: one row per (person, candidate) with features, and one row per person with the class
    auto-match | review | non-match
Rules (protocol Section 6):
  Block: candidate pairs share a normalized family-name key and the first given-name initial.
  Score: given-name agreement (full / initial / conflict); affiliation agreement (institution, else
         country); field compatibility (prespecified map); career plausibility (birth year, if known).
  Classify: auto-match = exactly one non-conflicting candidate, with a compatible FULL given name and
            agreement on affiliation (institution or country) or field;
            review = any other case with at least one non-conflicting candidate;
            non-match = no non-conflicting candidate.
"""
import json, os, sys
import pandas as pd
import pycountry

sys.path.insert(0, os.path.dirname(__file__))
from normalize import (split_stanford, family_keys, given_info, clean_given, ascii_fold,
                       inst_agree)

HERE = os.path.dirname(__file__)
FIELD_MAP = json.load(open(os.path.join(HERE, 'field_map.json')))

NICK = {'bill': 'william', 'will': 'william', 'bob': 'robert', 'rob': 'robert', 'bert': 'robert',
        'rick': 'richard', 'dick': 'richard', 'rich': 'richard', 'mike': 'michael', 'jim': 'james',
        'jamie': 'james', 'liz': 'elizabeth', 'beth': 'elizabeth', 'betty': 'elizabeth',
        'kate': 'katherine', 'kathy': 'katherine', 'cathy': 'catherine', 'tom': 'thomas',
        'joe': 'joseph', 'steve': 'stephen', 'dan': 'daniel', 'danny': 'daniel', 'dave': 'david',
        'chris': 'christopher', 'jenny': 'jennifer', 'jen': 'jennifer', 'maggie': 'margaret',
        'peggy': 'margaret', 'ed': 'edward', 'ted': 'edward', 'andy': 'andrew', 'tony': 'anthony',
        'pat': 'patricia', 'nick': 'nicholas', 'jon': 'jonathan', 'ben': 'benjamin', 'sam': 'samuel',
        'tim': 'timothy', 'pete': 'peter', 'larry': 'lawrence', 'harry': 'henry', 'hank': 'henry',
        'jack': 'john', 'johnny': 'john', 'chuck': 'charles', 'charlie': 'charles', 'greg': 'gregory',
        'matt': 'matthew', 'alex': 'alexander', 'sandy': 'alexander', 'fred': 'frederick',
        'jeff': 'jeffrey', 'ken': 'kenneth', 'ron': 'ronald', 'don': 'donald', 'doug': 'douglas',
        'phil': 'philip', 'gene': 'eugene', 'sue': 'susan', 'suzy': 'susan', 'debbie': 'deborah',
        'deb': 'deborah', 'barb': 'barbara', 'vicky': 'victoria', 'tricia': 'patricia',
        'abby': 'abigail', 'becky': 'rebecca', 'kim': 'kimberly', 'mandy': 'amanda', 'gerry': 'gerald',
        'jerry': 'gerald', 'stan': 'stanley', 'walt': 'walter', 'ray': 'raymond', 'vince': 'vincent'}


def canon_first(name):
    n = ascii_fold(name)
    return NICK.get(n, n)


_country_cache = {}


def to_iso3(c):
    """Country name or code -> lowercase ISO3 (Stanford convention); '' if unknown."""
    if c is None or (isinstance(c, float) and pd.isna(c)):
        return ''
    s = str(c).strip()
    if not s:
        return ''
    if s in _country_cache:
        return _country_cache[s]
    out = ''
    if len(s) == 3 and s.isalpha():
        out = s.lower()
    else:
        alias = {'usa': 'usa', 'us': 'usa', 'united states of america': 'usa', 'uk': 'gbr',
                 'england': 'gbr', 'scotland': 'gbr', 'wales': 'gbr', 'northern ireland': 'gbr',
                 'south korea': 'kor', 'korea': 'kor', 'republic of korea': 'kor', 'russia': 'rus',
                 'taiwan': 'twn', 'iran': 'irn', 'czech republic': 'cze', 'vietnam': 'vnm',
                 'hong kong': 'hkg', 'macau': 'mac', 'turkey': 'tur', 'the netherlands': 'nld'}
        if ascii_fold(s) in alias:
            out = alias[ascii_fold(s)]
        else:
            try:
                out = pycountry.countries.lookup(s).alpha_3.lower()
            except LookupError:
                try:
                    out = pycountry.countries.search_fuzzy(s)[0].alpha_3.lower()
                except LookupError:
                    out = ''
    _country_cache[s] = out
    return out


def given_agreement(crit_given, stan_given):
    """'full' | 'initial' | 'conflict'."""
    a, b = clean_given(crit_given), clean_given(stan_given)
    if not a or not b:
        return 'initial' if (a[:1] or b[:1]) else 'conflict'
    fa, fb = a[0], b[0]
    if len(fa) > 1 and len(fb) > 1 and canon_first(fa) == canon_first(fb):
        return 'full'
    if fa[0] != fb[0]:
        # 'Wei Ping' vs 'Weiping' style and first-initial mismatch are handled below
        if ''.join(a) != ''.join(b):
            return 'conflict'
    if len(fa) == 1 or len(fb) == 1:
        return 'initial' if fa[0] == fb[0] else 'conflict'
    if canon_first(fa) == canon_first(fb):
        return 'full'
    if ''.join(a) == ''.join(b) or ''.join(a).startswith(''.join(b)) or ''.join(b).startswith(''.join(a)):
        return 'full'  # concatenated given names (East Asian romanization)
    return 'conflict'


def field_compatible(source, field_hint, sm_field, sm_subfield):
    """True / False / None (no information)."""
    rule = FIELD_MAP['sources'].get(source)
    hint = (field_hint or '').strip()
    if hint:
        # an explicit Science-Metrix field or subfield name (benchmark, some lists)
        if hint == sm_field or hint == sm_subfield:
            return True
        sec = FIELD_MAP['sections'].get(hint)
        if sec is not None:
            return sm_field in sec['fields'] or sm_subfield in sec.get('subfields', [])
    if rule is None:
        return None
    if rule == 'any':
        return None
    return sm_field in rule['fields'] or sm_subfield in rule.get('subfields', [])


class StanfordIndex:
    def __init__(self, df):
        self.df = df.reset_index(drop=True)
        fg = self.df.authfull.map(split_stanford)
        self.df['_family'] = fg.map(lambda x: x[0])
        self.df['_given'] = fg.map(lambda x: x[1])
        self.df['_init'] = self.df._given.map(lambda g: given_info(g)['initial'])
        self.idx = {}
        for i, fam, ini in zip(self.df.index, self.df._family, self.df._init):
            for k in family_keys(fam):
                self.idx.setdefault((k, ini), set()).add(i)

    def block(self, family, given):
        gi = given_info(given)
        inits = {gi['initial'], canon_first(gi['first'])[:1]} - {''}
        out = set()
        for k in family_keys(family):
            for ini in inits:
                out |= self.idx.get((k, ini), set())
        return sorted(out)


def link(crit, index, birth_year_col=None):
    pairs, persons = [], []
    df = index.df
    for r in crit.itertuples(index=False):
        rc = r._asdict()
        cands = index.block(rc['family'], rc['given'])
        c_iso = to_iso3(rc.get('country'))
        rows = []
        for i in cands:
            s = df.loc[i]
            ga = given_agreement(rc['given'], s._given)
            if ga == 'conflict':
                continue
            inst = inst_agree(rc.get('affiliation') or '', s.inst_name or '')
            ctry = bool(c_iso) and c_iso == str(s.cntry)
            fc = field_compatible(rc['source'], rc.get('field_hint'), s['sm-field'], s['sm-subfield-1'])
            career = None
            by = rc.get(birth_year_col) if birth_year_col else None
            if by and not pd.isna(by) and not pd.isna(s.firstyr):
                career = (by + 18) <= s.firstyr <= (by + 40)
            rows.append(dict(person_id=rc['person_id'], stanford_row=int(i), authfull=s.authfull,
                             given_agree=ga, inst_agree=inst, country_agree=ctry,
                             affil_agree=inst or ctry, field_compat=fc, career_plausible=career))
        if not rows:
            cls, best = 'non-match', None
        elif (len(rows) == 1 and rows[0]['given_agree'] == 'full'
              and (rows[0]['affil_agree'] or rows[0]['field_compat'] is True)
              and rows[0]['career_plausible'] is not False):
            cls, best = 'auto-match', rows[0]['stanford_row']
        else:
            cls, best = 'review', None
        persons.append(dict(person_id=rc['person_id'], n_candidates=len(rows), link_class=cls,
                            auto_stanford_row=best))
        pairs += rows
    return pd.DataFrame(persons), pd.DataFrame(pairs)
