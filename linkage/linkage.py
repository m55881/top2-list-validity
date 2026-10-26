"""Record linkage between external recognition lists and the Stanford-Elsevier tables.

Implements protocol Section 6 (registered on OSF, October 2026). Fixed before any
outcome record is linked. Inputs are plain dicts/DataFrames; no source-specific
parsing happens here (parsers live in parsers.py).

External record fields used:
    rec_id, family, given, inst (free text, may be ''), country (ISO3 lowercase or ''),
    domain (key into FIELD_MAP, e.g. 'health', 'all', 'twas:03'), birth_year (optional)

Implementation decisions fixed with this code (documented in README):
  D1. A pair whose first given names conflict (both full and incompatible) is not a candidate.
  D2. First given names are 'full-compatible' when equal after normalization, or when one is a
      prefix of the other and the shorter has at least 3 letters (Chris/Christopher, Jean/Jean-Pierre).
  D3. If both records carry a middle initial and the first middle initials differ, the pair cannot
      be auto-matched (it goes to review).
  D4. Auto-match = exactly one candidate is full-compatible (and free of D3), that candidate agrees
      on affiliation (institution or country) or field, no other candidate agrees on institution, and
      career plausibility (when a birth year is known) is not violated. Everything else with at least
      one candidate goes to review.
  D5. Institution agreement = the sets of distinctive institution tokens (generic words removed)
      overlap with Jaccard >= 0.5, or one set contains the other. Country agreement = equal ISO3 code.
"""
import json
import os
import re
from collections import defaultdict

import pandas as pd
from unidecode import unidecode

HERE = os.path.dirname(os.path.abspath(__file__))
FIELD_MAP = json.load(open(os.path.join(HERE, 'field_map.json')))

TITLES = {'prof', 'professor', 'dr', 'sir', 'dame', 'mr', 'mrs', 'ms', 'lord', 'baroness', 'lady',
          'emeritus', 'assoc', 'associate', 'a/prof', 'aprof', 'mx'}
POSTNOMINALS = {'frs', 'formemrs', 'fmedsci', 'freng', 'fba', 'frse', 'cbe', 'obe', 'mbe', 'kbe', 'dbe',
                'kt', 'ac', 'ao', 'am', 'oc', 'cm', 'faa', 'fahms', 'facp', 'frcp', 'frcs', 'md', 'phd',
                'jr', 'sr', 'ii', 'iii', 'iv', 'mph', 'msc', 'bsc', 'mbbs', 'dphil', 'frcpath', 'fcahs',
                'frsc', 'frsb', 'flsw', 'fls', 'cb', 'dcmg', 'kcmg', 'cmg', 'fras', 'fias'}
PARTICLES = {'van', 'von', 'der', 'den', 'de', 'del', 'della', 'di', 'da', 'dos', 'das', 'do', 'du', 'la',
             'le', 'ter', 'ten', 'el', 'al', 'bin', 'ibn', 'mac', 'st', 'y'}
INST_STOP = {'university', 'universite', 'universitat', 'universiteit', 'universita', 'universidad',
             'universidade', 'univ', 'of', 'the', 'and', 'school', 'college', 'institute', 'institut',
             'instituto', 'istituto', 'faculty', 'department', 'dept', 'center', 'centre', 'centro',
             'hospital', 'hospitals', 'medical', 'medicine', 'health', 'sciences', 'science', 'research',
             'national', 'foundation', 'trust', 'nhs', 'inc', 'ltd', 'de', 'la', 'le', 'des', 'du',
             'di', 'del', 'der', 'fur', 'for', 'in', 'at', 'graduate', 'clinical', 'campus', 'division',
             'laboratory', 'laboratories', 'lab', 'group', 'unit', 'program', 'programme', 'system',
             'technology', 'academy', 'council', 'state', 'city', 'general', 'public', 'private'}

_ISO3 = None


def ascii_lower(s):
    return unidecode(str(s or '')).lower()


def clean_tokens(s):
    s = ascii_lower(s)
    s = re.sub(r'\([^)]*\)', ' ', s)          # nicknames, maiden names in brackets
    s = s.replace('.', ' ').replace(',', ' ').replace("'", '').replace('`', '')
    s = re.sub(r'[^a-z\- ]', ' ', s)
    return [t for t in s.split() if t]


def norm_family(family):
    toks = [t for t in clean_tokens(family) if t not in POSTNOMINALS]
    return toks


def family_keys(family):
    """All blocking keys for a family name (D: particles with and without, hyphen and space parts)."""
    toks = norm_family(family)
    if not toks:
        return set()
    keys = set()
    joined = ''.join(toks).replace('-', '')
    keys.add(joined)
    core = [t for t in toks if t not in PARTICLES]
    if core:
        keys.add(''.join(core).replace('-', ''))
    parts = []
    for t in core or toks:
        parts.extend([p for p in t.split('-') if p and p not in PARTICLES])
    for p in parts:
        if len(p) >= 2:
            keys.add(p)
    return keys


def norm_given(given):
    """Return (first_given, middle_initials). Hyphens inside a given name are joined (Xiao-Ming -> xiaoming)."""
    toks = [t for t in clean_tokens(given) if t not in TITLES and t not in POSTNOMINALS]
    toks = [t.replace('-', '') for t in toks]
    toks = [t for t in toks if t]
    if not toks:
        return '', ''
    # "J.R.R." style initials glued together
    first = toks[0]
    rest = toks[1:]
    if len(first) > 1 and len(rest) == 0 and re.fullmatch(r'[a-z]{2,3}', first) and given and '.' in str(given):
        rest = list(first[1:])
        first = first[0]
    mids = ''.join(t[0] for t in rest)
    return first, mids


def given_agreement(g1, g2):
    """'full', 'initial' or 'conflict' for first given names (D1, D2)."""
    if not g1 or not g2:
        return 'initial'                          # given name missing on one side: weakest agreement
    if g1[0] != g2[0]:
        return 'conflict'
    if len(g1) == 1 or len(g2) == 1:
        return 'initial'
    if g1 == g2:
        return 'full'
    short, long_ = sorted([g1, g2], key=len)
    if len(short) >= 3 and long_.startswith(short):
        return 'full'
    return 'conflict'


def inst_tokens(s):
    toks = [t for t in re.split(r'[^a-z]+', ascii_lower(s)) if t]
    return {t for t in toks if t not in INST_STOP and len(t) > 1}


def inst_agree(a, b):
    ta, tb = inst_tokens(a), inst_tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    if inter == 0:
        return False
    return inter / len(ta | tb) >= 0.5 or ta <= tb or tb <= ta


def iso3(country):
    """Map a country name or code to lowercase ISO3 ('' if unknown)."""
    global _ISO3
    if not country or (isinstance(country, float)):
        return ''
    c = str(country).strip()
    if re.fullmatch(r'[a-z]{3}', c):
        return c
    if _ISO3 is None:
        import pycountry
        _ISO3 = {}
        for x in pycountry.countries:
            for nm in [x.name, getattr(x, 'common_name', None), getattr(x, 'official_name', None), x.alpha_2, x.alpha_3]:
                if nm:
                    _ISO3[ascii_lower(nm)] = x.alpha_3.lower()
        _ISO3.update({'uk': 'gbr', 'united kingdom': 'gbr', 'england': 'gbr', 'scotland': 'gbr', 'wales': 'gbr',
                      'northern ireland': 'gbr', 'great britain': 'gbr', 'usa': 'usa', 'us': 'usa',
                      'united states': 'usa', 'united states of america': 'usa', 'south korea': 'kor',
                      'korea': 'kor', 'republic of korea': 'kor', 'taiwan': 'twn', 'iran': 'irn',
                      'russia': 'rus', 'hong kong': 'hkg', 'macau': 'mac', 'vietnam': 'vnm', 'turkey': 'tur',
                      'turkiye': 'tur', 'czech republic': 'cze', 'the netherlands': 'nld', 'holland': 'nld',
                      'el': 'grc', 'uk/eu': 'gbr', 'tanzania': 'tza', 'venezuela': 'ven', 'bolivia': 'bol',
                      'syria': 'syr', 'laos': 'lao', 'moldova': 'mda', 'palestine': 'pse', 'ivory coast': 'civ',
                      "cote d'ivoire": 'civ', 'democratic republic of the congo': 'cod', 'dr congo': 'cod'})
    return _ISO3.get(ascii_lower(c), '')


def field_ok(domain, sm_field):
    if not domain:
        return False
    allowed = FIELD_MAP.get(domain)
    if allowed is None:
        return False
    return sm_field in allowed


class StanfordIndex:
    """Blocking index over a Stanford table (one row per listed scientist)."""

    def __init__(self, df):
        self.df = df.reset_index(drop=True)
        fam, giv = [], []
        for a in self.df['authfull'].astype(str):
            f, _, g = a.partition(',')
            fam.append(f.strip())
            giv.append(g.strip())
        self.family = fam
        self.given = giv
        self.gnorm = [norm_given(g) for g in giv]
        self.index = defaultdict(list)
        for i, (f, (g1, _)) in enumerate(zip(fam, self.gnorm)):
            ini = g1[:1]
            for k in family_keys(f):
                self.index[(k, ini)].append(i)

    def candidates(self, family, given):
        g1, _ = norm_given(given)
        ini = g1[:1]
        out = set()
        for k in family_keys(family):
            out.update(self.index.get((k, ini), []))
        return sorted(out)


def score_pair(rec, idx, i):
    g1, m1 = norm_given(rec.get('given', ''))
    g2, m2 = idx.gnorm[i]
    row = idx.df.iloc[i]
    gn = given_agreement(g1, g2)
    mid_conflict = bool(m1 and m2 and m1[0] != m2[0])
    inst_ok = inst_agree(rec.get('inst', ''), row['inst_name'])
    ctry_ok = bool(rec.get('country')) and rec.get('country') == row['cntry']
    fld_ok = field_ok(rec.get('domain', ''), row['sm-field'])
    career_ok = None
    by = rec.get('birth_year')
    if by and not pd.isna(by) and not pd.isna(row['firstyr']):
        career_ok = (by + 18) <= row['firstyr'] <= (by + 40)
    return dict(stanford_row=int(i), authfull=row['authfull'], inst_name=row['inst_name'], cntry=row['cntry'],
                sm_field=row['sm-field'], firstyr=row['firstyr'], given_agreement=gn,
                middle_conflict=mid_conflict, inst_agree=inst_ok, country_agree=ctry_ok,
                affil_agree=inst_ok or ctry_ok, field_agree=fld_ok, career_plausible=career_ok)


def classify(rec, idx):
    """Return (decision, candidates) with decision in {'auto_match', 'review', 'non_match'}."""
    cands = []
    for i in idx.candidates(rec.get('family', ''), rec.get('given', '')):
        s = score_pair(rec, idx, i)
        if s['given_agreement'] == 'conflict':      # D1
            continue
        if s['career_plausible'] is False:
            s['career_flag'] = True
        cands.append(s)
    if not cands:
        return 'non_match', cands
    full = [c for c in cands if c['given_agreement'] == 'full' and not c['middle_conflict']]
    if len(cands) == 1 and len(full) == 1 and (full[0]['affil_agree'] or full[0]['field_agree']) \
            and not full[0].get('career_flag'):
        return 'auto_match', cands
    if len(full) == 1 and len(cands) > 1:
        # exactly one full-compatible candidate among several: D4 allows auto-match only if
        # no other candidate agrees on institution
        others_inst = any(c['inst_agree'] for c in cands if c is not full[0])
        if (full[0]['affil_agree'] or full[0]['field_agree']) and not others_inst and not full[0].get('career_flag'):
            return 'auto_match', cands
    return 'review', cands


def link_all(records, idx):
    """records: iterable of dicts. Returns a DataFrame with one row per record."""
    out = []
    for r in records:
        dec, cands = classify(r, idx)
        best = None
        if dec == 'auto_match':
            best = [c for c in cands if c['given_agreement'] == 'full' and not c['middle_conflict']][0]
        out.append(dict(rec_id=r['rec_id'], decision=dec, n_candidates=len(cands),
                        matched_row=best['stanford_row'] if best else None,
                        matched_authfull=best['authfull'] if best else None,
                        candidates=json.dumps(cands, default=str)))
    return pd.DataFrame(out)


def top_similar(rec, idx, k=10, _cache={}):
    """The k most similar Stanford names for a non-matched record (for AI review of non-matches)."""
    from rapidfuzz import process, fuzz
    key = id(idx)
    if key not in _cache:
        _cache.clear()
        _cache[key] = [' '.join(clean_tokens(f)) + ' ' + ' '.join(clean_tokens(g)) for f, g in zip(idx.family, idx.given)]
    names = _cache[key]
    q = ' '.join(clean_tokens(rec.get('family', ''))) + ' ' + ' '.join(clean_tokens(rec.get('given', '')))
    hits = process.extract(q, names, scorer=fuzz.token_sort_ratio, limit=k)
    return [dict(stanford_row=int(i), authfull=idx.df.iloc[i]['authfull'], inst_name=idx.df.iloc[i]['inst_name'],
                 cntry=idx.df.iloc[i]['cntry'], sm_field=idx.df.iloc[i]['sm-field'], similarity=round(s, 1))
            for _, s, i in hits]
