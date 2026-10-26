"""Name and institution normalization for record linkage (protocol Section 6).

Fixed before any criterion record is linked to list status.
"""
import re
import unicodedata

TITLES = {
    'prof', 'professor', 'dr', 'sir', 'dame', 'mr', 'mrs', 'ms', 'miss', 'lord', 'lady',
    'baroness', 'baron', 'rev', 'md', 'phd', 'dphil', 'jr', 'sr', 'ii', 'iii', 'iv',
}
POSTNOMINALS = {
    'frs', 'formemrs', 'fmedsci', 'freng', 'fba', 'frse', 'cbe', 'obe', 'mbe', 'kbe', 'dbe',
    'kt', 'ac', 'ao', 'am', 'oc', 'cm', 'facp', 'frcp', 'frcs', 'frcpath', 'frcpsych', 'frcog',
    'facs', 'mph', 'mba', 'msc', 'scd', 'dsc', 'mbbs', 'mbchb', 'bm', 'bch', 'rn', 'pharmd',
    'dds', 'dmd', 'drph', 'ms', 'ma', 'bs', 'ba', 'jd', 'dvm', 'faha', 'facc', 'fahms', 'faa',
    'faahms', 'fcahs', 'frsc', 'fras', 'mbbch', 'bmedsci', 'frcpc', 'frcsc', 'frcpe', 'frcpi',
}
PARTICLES = {'van', 'von', 'de', 'der', 'den', 'del', 'della', 'di', 'da', 'dos', 'das', 'du',
             'la', 'le', 'ten', 'ter', 'bin', 'ibn', 'al', 'el', 'af', 'zu', 'vom', 'dello', 'st'}


def ascii_fold(s):
    """Accents removed, special letters transliterated, lowercase."""
    if s is None:
        return ''
    s = str(s)
    for a, b in {'ß': 'ss', 'ø': 'o', 'Ø': 'O', 'æ': 'ae', 'Æ': 'AE', 'œ': 'oe', 'Œ': 'OE',
                 'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ı': 'i', 'þ': 'th', 'ð': 'd'}.items():
        s = s.replace(a, b)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.encode('ascii', 'ignore').decode().lower()


def tokens(s):
    s = ascii_fold(s)
    s = re.sub(r"[’'`]", '', s)          # O'Brien -> obrien
    s = re.sub(r'[^a-z\- ]+', ' ', s)
    return [t for t in s.replace('-', ' - ').split() if t]


def clean_given(given):
    toks = [t for t in tokens(given) if t != '-' and t not in TITLES and t not in POSTNOMINALS]
    return toks


def family_keys(family):
    """All blocking keys for a family name: full (no spaces/hyphens), without particles,
    and each hyphen part."""
    # family names are already parsed: never drop tokens such as 'Ma', 'Lord' or 'Am' here
    toks = tokens(family)
    if not toks:
        return set()
    keys = set()
    full = ''.join(t for t in toks if t != '-')
    keys.add(full)
    core = [t for t in toks if t != '-' and t not in PARTICLES]
    if core:
        keys.add(''.join(core))
    if '-' in toks:
        for part in ' '.join(toks).split('-'):
            p = [t for t in part.split() if t not in PARTICLES]
            if p:
                keys.add(''.join(p))
    # last token alone for multi-word family names (e.g. Spanish double surnames)
    if len(core) > 1:
        keys.add(core[-1])
        keys.add(core[0])
    return {k for k in keys if len(k) >= 2}


def split_stanford(authfull):
    """'Family, Given M.' -> (family, given)."""
    if authfull is None:
        return '', ''
    s = str(authfull)
    if ',' in s:
        fam, giv = s.split(',', 1)
        return fam.strip(), giv.strip()
    parts = s.split()
    return (parts[-1], ' '.join(parts[:-1])) if parts else ('', '')


def split_natural(name):
    """'Given Middle Family' -> (family, given), keeping particles with the family name.
    Post-nominals are removed only after a comma or when written in capitals/with periods at the
    end (so the surname 'Ma' is kept but 'MA' or 'M.A.' after a name is dropped); titles only at
    the start."""
    s = str(name).strip()
    if ',' in s:
        s = s.split(',', 1)[0]
    toks = [t for t in re.split(r'\s+', s) if t]
    while toks and ascii_fold(toks[0]).strip('.,') in TITLES:
        toks = toks[1:]
    while len(toks) > 2 and (toks[-1].isupper() or '.' in toks[-1][1:]) and \
            ascii_fold(toks[-1]).replace('.', '').strip(',') in POSTNOMINALS | TITLES:
        toks = toks[:-1]
    if not toks:
        return '', ''
    i = len(toks) - 1
    while i > 1 and ascii_fold(toks[i - 1]).strip('.') in PARTICLES:
        i -= 1
    return ' '.join(toks[i:]), ' '.join(toks[:i])


def given_info(given):
    g = clean_given(given)
    first = g[0] if g else ''
    return {'first': first, 'initial': first[:1], 'all': g,
            'first_is_initial': len(first) <= 1}


INST_STOP = {'the', 'of', 'and', 'for', 'at', 'in', 'de', 'du', 'des', 'la', 'le', 'der', 'die',
             'und', 'di', 'del', 'y', 'e', 'school', 'faculty', 'department', 'dept', 'institute',
             'center', 'centre', 'university', 'universitat', 'universite', 'universita',
             'universidad', 'universiteit', 'college', 'hospital', 'medical', 'medicine',
             'sciences', 'science', 'research', 'national', 'health', 'campus', 'inc', 'ltd'}


def inst_tokens(s):
    return {t for t in tokens(s) if t != '-' and t not in INST_STOP and len(t) > 2}


def inst_agree(a, b):
    """Institution agreement: shares a distinctive token (e.g. 'harvard', 'karolinska')."""
    ta, tb = inst_tokens(a), inst_tokens(b)
    return bool(ta and tb and ta & tb)


# ---- distinctive institution tokens (document frequency across the 18,501 distinct
# Stanford v2 institution names; frozen in inst_token_df.json)
import json as _json, os as _os
_DF = _json.load(open(_os.path.join(_os.path.dirname(__file__), 'inst_token_df.json')))
GENERIC_INST = {'dental', 'children', 'childrens', 'cancer', 'heart', 'eye', 'pediatric', 'paediatric',
                'veterans', 'affairs', 'memorial', 'general', 'royal', 'state', 'federal', 'central',
                'north', 'south', 'east', 'west', 'northern', 'southern', 'eastern', 'western', 'new',
                'saint', 'san', 'santa', 'city', 'regional', 'county', 'women', 'womens', 'mens',
                'catholic', 'christian', 'baptist', 'methodist', 'presbyterian', 'polytechnic',
                'technical', 'technology', 'agricultural', 'normal', 'teaching', 'clinic', 'clinical',
                'kings', 'queens', 'imperial', 'american', 'chinese', 'max', 'planck'}
DISTINCT_MAX_DF = 30


def distinctive_tokens(s, max_df=DISTINCT_MAX_DF):
    """Institution words that identify an institution (e.g. 'harvard', 'karolinska'):
    not generic, and used by at most max_df distinct Stanford institution names
    (words never seen in the Stanford table count as distinctive)."""
    return {t for t in inst_tokens(s) if t not in GENERIC_INST and _DF.get(t, 0) <= max_df}


def inst_agree(a, b):  # noqa: F811  (supersedes the simple version above)
    da, db = distinctive_tokens(a), distinctive_tokens(b)
    return bool(da and db and da & db)
