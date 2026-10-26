"""Standardize all criterion lists (academy elections and grant awards, 2020-2025) into one
award-level table and one person-level table. Parsing only: no record is linked to the
Stanford-Elsevier list here.

Outputs (data/derived/):
  criterion_awards.csv   one row per election or award
  criterion_people.csv   one row per distinct person within each source
  criterion_counts.json  counts per source and year, for checking against official totals
"""
import glob, io, json, os, re, sys
import pandas as pd
import pdfplumber
import pycountry

sys.path.insert(0, '/home/claude/linkage')
from normalize import split_natural, split_stanford, ascii_fold, clean_given, TITLES

OFF = '/home/claude/data/official/'
RAW = '/home/claude/grants/raw/'
P2 = '/home/claude/grants/part2_raw/grant_lists_2020-2025_part2/'
OUT = '/home/claude/data/derived/'
rows = []


def add(source, year, family, given, affiliation='', country='', field_hint='', category='',
        raw_name='', ext_id='', scheme='', primary=True):
    rows.append(dict(source=source, year=int(year), category=category, family=str(family).strip(),
                     given=str(given).strip(), affiliation=str(affiliation or '').strip(),
                     country=str(country or '').strip().lower(), field_hint=str(field_hint or '').strip(),
                     raw_name=str(raw_name).strip(), ext_id=str(ext_id or ''), scheme=scheme,
                     primary=bool(primary)))


def iso3_from_text(s):
    s = (s or '').strip().strip('.')
    if not s:
        return ''
    try:
        return pycountry.countries.lookup(s).alpha_3.lower()
    except LookupError:
        alias = {'uk': 'gbr', 'united kingdom': 'gbr', 'england': 'gbr', 'scotland': 'gbr', 'wales': 'gbr',
                 'south korea': 'kor', 'korea': 'kor', 'taiwan': 'twn', 'russia': 'rus', 'iran': 'irn',
                 'the netherlands': 'nld', 'hong kong': 'hkg', 'vietnam': 'vnm', 'turkey': 'tur',
                 'czech republic': 'cze', 'tanzania': 'tza', 'usa': 'usa', 'u.s.': 'usa'}
        return alias.get(ascii_fold(s), '')


def strip_person_name(s):
    """Remove leading titles and trailing post-nominal capitals from a natural-order name."""
    toks = s.replace(' ', ' ').split()
    while toks and ascii_fold(toks[0]).strip('.,') in TITLES | {'professor', 'prof'}:
        toks = toks[1:]
    while len(toks) > 2 and re.fullmatch(r'[A-Z][A-Za-z]*[A-Z]+[a-z]*|[A-Z]{2,}|Kt|FMedSci|FRSE|FREng|FLSW|FAcSS|HonFMedSci', toks[-1]):
        toks = toks[:-1]
    return ' '.join(toks)


# ---------------------------------------------------------------- NAM and AMS
for f in sorted(glob.glob(OFF + 'medical/*NAM_new_members_*.txt')):
    year = int(re.search(r'(\d{4})\.txt$', f).group(1))
    section = None
    for line in open(f, encoding='utf-8'):
        line = line.strip()
        if line.startswith('##'):
            section = 'international' if 'international' in line.lower() else 'regular'
            continue
        if section is None or not line:
            continue
        name = line.split(',', 1)[0]
        aff = line.split(',', 1)[1] if ',' in line else ''
        fam, giv = split_natural(name)
        ctry = 'usa'
        if section == 'international':
            segs = [x.strip() for x in aff.split(',') if x.strip()]
            ctry = next((iso3_from_text(x) for x in reversed(segs[-3:]) if iso3_from_text(x)), '')
        add('NAM', year, fam, giv, aff, ctry, '', section, line[:120])

for f in sorted(glob.glob(OFF + 'medical/*AMS_new_Fellows_*.txt')):
    year = int(re.search(r'(\d{4})\.txt$', f).group(1))
    started = False
    for line in open(f, encoding='utf-8'):
        line = line.strip()
        if line.startswith('##'):
            started = True
            continue
        if not started or not line:
            continue
        name = strip_person_name(line.split(',', 1)[0])
        aff = line.split(',', 1)[1] if ',' in line else ''
        fam, giv = split_natural(name)
        # AMS Fellows are elected for UK-based or UK-linked work; country taken as UK
        add('AMS', year, fam, giv, aff, 'gbr', '', 'fellow', line[:120])

# ---------------------------------------------------------------- NAS, Royal Society, TWAS (parsed earlier)
ce = pd.read_csv('/home/claude/data/derived/criterion_elections.csv')
for r in ce.itertuples(index=False):
    if r.source == 'RoyalSociety' and r.category == 'honorary':
        continue
    ctry = iso3_from_text(r.country) if isinstance(r.country, str) else ''
    if r.source == 'TWAS':
        res = getattr(r, 'residence', '')
        ctry = iso3_from_text(res if isinstance(res, str) else '') or ctry
        add('TWAS', r.year, r.family, r.given, r.affiliation if isinstance(r.affiliation, str) else '', ctry,
            r.section if isinstance(r.section, str) else '', r.category, f'{r.given} {r.family}')
    else:
        if r.source == 'NAS' and r.category.startswith('member'):
            ctry = 'usa'
        add(r.source, r.year, r.family, r.given, r.affiliation if isinstance(r.affiliation, str) else '', ctry,
            '', r.category, f'{r.given} {r.family}')


# ---------------------------------------------------------------- grants
def read_hash_csv(f):
    lines = open(f, encoding='utf-8-sig', errors='replace').read().splitlines()
    return pd.read_csv(io.StringIO('\n'.join(l for l in lines if not l.startswith('#'))), dtype=str)


# NIH R01 (types 1 and 2)
nih_seen = set()
for f in sorted(glob.glob(RAW + 'grant_lists_2020-2025_NIH/*/GRANT_NIH_R01_*.csv')):
    lines = open(f, encoding='utf-8-sig', errors='replace').read().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith('"NIH Spending'))
    df = pd.read_csv(io.StringIO('\n'.join(lines[i:])), dtype=str, low_memory=False)
    df = df[df.Type.isin(['1', '2'])].drop_duplicates('Application ID')  # one row per award (RePORTER repeats rows per funding IC)
    df = df[~df['Application ID'].isin(nih_seen)]
    nih_seen.update(df['Application ID'])
    for r in df.itertuples(index=False):
        d = r._asdict()
        fam, giv = split_stanford(d['_21'])  # 'Contact PI / Project Leader'
        add('NIH_R01', d['_45'], fam, giv, d['_33'], iso3_from_text(d['_38'].title() if isinstance(d['_38'], str) else '') or 'usa',
            '', 'new' if d['Type'] == '1' else 'renewal', d['_21'], 'nihpid:' + str(d['_20']), 'R01')

# MRC
mrc_no_pi = []
COUNTRY_NAMES = sorted({ascii_fold(c.name) for c in pycountry.countries} | {'gambia', 'bahia', 'uganda'}, key=len, reverse=True)


def mrc_country(org, ctry):
    # GtR gives no country: MRC lead organisations are UK unless the name names another country
    if isinstance(ctry, str) and ctry.strip():
        return iso3_from_text(ctry)
    o = ascii_fold(org)
    if 'bahia' in o or 'brazil' in o:
        return 'bra'
    for c in COUNTRY_NAMES:
        if c not in ('united kingdom',) and re.search(r'\b' + re.escape(c) + r'\b', o):
            return iso3_from_text(c)
    return 'gbr'

for f in sorted(glob.glob(RAW + 'grant_lists_2020-2025_MRC/*/GRANT_MRC_*.csv')):
    df = read_hash_csv(f)
    for r in df.itertuples(index=False):
        if not isinstance(r.PISurname, str) or not r.PISurname.strip():
            mrc_no_pi.append(r.project_id)  # no principal investigator published: cannot be linked
            continue
        giv = ' '.join(x for x in [r.PIFirstName, r.PIOtherNames] if isinstance(x, str))
        add('MRC', r.award_year, r.PISurname, giv, r.organization, mrc_country(r.organization, r.country),
            '', r.scheme, r.lead_investigator_name, 'gtrpi:' + str(r.PIId), r.scheme)

# Wellcome
# H&SS awards count only if classified health-related by both AI classifiers (protocol Section 9)
_wc = pd.read_csv('/home/claude/linkage/classification/wellcome_hss_classification.csv', dtype=str)
WELLCOME_HSS_HEALTH = set(_wc[_wc.final == 'yes'].project_id)
for f in sorted(glob.glob(RAW + 'grant_lists_2020-2025_WELLCOME/*/GRANT_WELLCOME_*.csv')):
    df = read_hash_csv(f)
    for r in df.itertuples(index=False):
        fam, giv = split_natural(strip_person_name(r.lead_investigator_name))
        add('Wellcome', r.award_year, fam, giv, r.organization, iso3_from_text(r.country) if isinstance(r.country, str) else '',
            '', r.scheme, r.lead_investigator_name, '', r.scheme,
            primary=(r.scheme != 'Investigator Award in H&SS') or (r.project_id in WELLCOME_HSS_HEALTH))

# CIHR Project Grant (Bridge Grants kept, flagged as not primary)
for f in sorted(glob.glob(P2 + 'GRANT_CIHR_*.csv')):
    df = read_hash_csv(f)
    for r in df.itertuples(index=False):
        fam, giv = split_stanford(r.lead_investigator_name)
        add('CIHR', r.award_year, fam, giv, r.organization, iso3_from_text(r.country) or 'can', '',
            r.award_kind, r.lead_investigator_name, 'cihr:' + str(r.project_id), 'Project Grant',
            primary=(r.award_kind == 'Project Grant'))

# KAKEN (S) and (A): romanized names from KAKEN researcher profiles
rom = pd.read_csv('/home/claude/grants/KAKEN_PI_romanized_names_v2.csv', comment='#', dtype=str)
rom_by_num = dict(zip(rom.researcher_number.fillna(''), rom.romanized_name))
rom_by_kanji = dict(zip(rom.kanji_name, rom.romanized_name))
for f in sorted(glob.glob(P2 + 'GRANT_KAKEN_*.csv')):
    cat = re.search(r'KAKEN_([SA])_(\d{4})', f)
    df = pd.read_csv(f, dtype=str)
    for r in df.itertuples(index=False):
        pi = getattr(r, '_4')  # Principal Investigator
        m = re.search(r'\((\d{8})\)\s*$', pi)
        num = m.group(1) if m else ''
        kanji = ' '.join(pi.split()[:2])
        rn = rom_by_num.get(num) or rom_by_kanji.get(kanji) or ''
        toks = rn.split()
        fam, giv = (toks[0], ' '.join(toks[1:])) if len(toks) >= 2 else ('', '')
        sec = getattr(r, '_13')  # Review Section
        add('KAKEN', cat.group(2), fam.title() if fam.isupper() else fam, giv, getattr(r, '_15'), 'jpn', '',
            cat.group(1), pi, 'kaken:' + num, f'Kiban {cat.group(1)}',
            primary=True)
        rows[-1]['kaken_section'] = sec

# NHMRC Investigator Grants
for f in sorted(glob.glob(P2 + 'GRANT_NHMRC_*.xlsx')):
    year = int(re.search(r'(\d{4})', f).group(1))
    x = pd.read_excel(f, sheet_name='GRANTS DATA', engine='calamine', dtype=str)
    tcol = 'Grant Type' if 'Grant Type' in x else 'Funding Scheme'
    ncol = 'CIA Name' if 'CIA Name' in x else 'Chief Investigator A (Project Lead)'
    icol = 'Admin Institution' if 'Admin Institution' in x else 'Administering Institution'
    scol = 'Sub Type' if 'Sub Type' in x else 'Level, Stream or Sub-Type'
    x = x[x[tcol].astype(str).str.contains('Investigator Grant')]
    for r in x.itertuples(index=False):
        d = r._asdict() if False else dict(zip(x.columns, r))
        fam, giv = split_natural(strip_person_name(str(d[ncol])))
        orcid = d.get('CIA ORCID ID', '')
        add('NHMRC', year, fam, giv, d[icol], 'aus', '', str(d[scol]).strip(), d[ncol],
            'orcid:' + str(orcid) if isinstance(orcid, str) and orcid.strip() else '', 'Investigator Grant')

# ERC Advanced and Consolidator, Life Sciences
erc_counts = {}
A2 = {c.alpha_2: c.alpha_3.lower() for c in pycountry.countries}
A2.update({'UK': 'gbr', 'EL': 'grc'})
for f in sorted(glob.glob(P2 + 'GRANT_ERC_*_LS.pdf')):
    m = re.search(r'ERC_(ADG|COG)_(\d{4})_LS', f)
    n = 0
    with pdfplumber.open(f) as pdf:
        for page in pdf.pages:
            for t in page.extract_tables():
                for row in t:
                    cells = [(c or '').replace('\n', ' ').strip() for c in row]
                    if not cells or not re.fullmatch(r'LS\d{1,2}', cells[-1] or ''):
                        continue
                    last, first = cells[0], cells[1]
                    insts = [c for c in cells[2:-3] if c and not re.fullmatch(r'[A-Z]{2}', c)]
                    cc = next((c for c in cells[2:-1] if re.fullmatch(r'[A-Z]{2}', c)), '')
                    add('ERC_LS', m.group(2), last.title() if last.isupper() else last, first,
                        ' | '.join(dict.fromkeys(insts)), A2.get(cc, ''), cells[-1], m.group(1),
                        f'{first} {last}', '', 'AdG' if m.group(1) == 'ADG' else 'CoG')
                    n += 1
    erc_counts[f'{m.group(1)}_{m.group(2)}'] = n

# ---------------------------------------------------------------- outputs
aw = pd.DataFrame(rows)
aw['nfam'] = aw.family.map(lambda s: ''.join(ch for ch in ascii_fold(s) if ch.isalpha()))
aw['ngiv'] = aw.given.map(lambda s: (clean_given(s) or [''])[0])


def person_key(r):
    if r.ext_id and not r.ext_id.endswith(':') and r.ext_id.split(':', 1)[1] not in ('', 'nan'):
        if r.ext_id.split(':')[0] in ('nihpid', 'gtrpi', 'kaken', 'orcid'):
            return f'{r.source}|{r.ext_id}'
    return f'{r.source}|{r.nfam}|{r.ngiv}'


aw['person_key'] = aw.apply(person_key, axis=1)
os.makedirs(OUT, exist_ok=True)
aw.to_csv(OUT + 'criterion_awards.csv', index=False)

ppl = (aw.sort_values('year').groupby('person_key', as_index=False)
       .agg(source=('source', 'first'), family=('family', 'first'), given=('given', 'first'),
            affiliation=('affiliation', 'last'), country=('country', 'last'), field_hint=('field_hint', 'first'),
            first_year=('year', 'min'), n_awards=('year', 'size'), any_primary=('primary', 'max'),
            categories=('category', lambda s: ';'.join(sorted(set(map(str, s)))))))
ppl.insert(0, 'person_id', ['P%06d' % i for i in range(1, len(ppl) + 1)])
ppl.to_csv(OUT + 'criterion_people.csv', index=False)

counts = {'awards_by_source_year': {f'{k[0]}|{k[1]}': int(v) for k, v in aw.groupby(['source', 'year']).size().items()},
          'awards_by_source': aw.groupby('source').size().to_dict(),
          'primary_awards_by_source': aw[aw.primary].groupby('source').size().to_dict(),
          'people_by_source': ppl.groupby('source').size().to_dict(),
          'erc_names_parsed': erc_counts,
          'mrc_awards_without_named_pi': len(mrc_no_pi), 'blank_family': int((aw.family == '').sum()), 'blank_given': int((aw.given == '').sum())}
json.dump(counts, open(OUT + 'criterion_counts.json', 'w'), indent=1, default=int)
print(json.dumps({k: v for k, v in counts.items() if k != 'awards_by_source_year'}, indent=1, default=int))
