"""Parse official election lists (NAS, Royal Society, TWAS) 2020-2025 into one table.

Output: data/derived/criterion_elections.csv with one row per person-election.
No linkage to the Stanford list happens here.
"""
import glob, re, sys, unicodedata
import pandas as pd
from bs4 import BeautifulSoup

D = '/home/claude/data/official/'
OUT = '/home/claude/data/derived/'
rows = []


def html_text(path):
    s = BeautifulSoup(open(path, encoding='utf-8', errors='ignore'), 'html.parser')
    for t in s(['script', 'style']):
        t.decompose()
    return s.get_text('\n')


def add(src, year, cat, family, given, affil='', country='', extra=None):
    r = dict(source=src, year=year, category=cat, family=family.strip(),
             given=given.strip(), affiliation=affil.strip(), country=country.strip())
    r.update(extra or {})
    rows.append(r)


# ---------- NAS press releases (2023, 2024, 2025): "Family, Given; affiliation" ----------
def nas_press(text, year):
    text = text.replace('\r', '')
    body = text.split('time of election are:', 1)[1]
    mem, intl = body.split('Newly elected international members', 1)
    intl = intl.split('country of citizenship are:', 1)[1].split('The National Academy of Sciences is', 1)[0]
    post = ''
    if 'Elected posthumously' in mem:
        mem, post = mem.split('Elected posthumously', 1)
        post = post.split(':', 1)[1]
    pat = re.compile(r'^\s*([^\n;]{2,60}?), ([^\n;]{1,60}?);\s*(.*)$', re.M)
    for part, cat in [(mem, 'member'), (post, 'member_posthumous'), (intl, 'international')]:
        for m in pat.finditer(part):
            aff = m.group(3)
            ctry = ''
            if cat == 'international':
                cm = re.search(r'\(([^()]*)\)\s*$', aff)
                ctry = cm.group(1) if cm else ''
            add('NAS', year, cat, m.group(1), m.group(2), aff, ctry)


for f, y in [('8c4c5e9e-NAS_2023_election.txt', 2023), ('94382c6f-NAS_2025_election.txt', 2025)]:
    nas_press(open(D + f, encoding='utf-8').read(), y)
# 2024 HTML: lines are separated; collapse to one entry per line
t24 = html_text(glob.glob(D + '*Members_-_NAS.html')[0])
t24 = re.sub(r'\n\s*\n+', '\n', t24)
nas_press(t24, 2024)

# ---------- NAS directory (2020-2022): "Given Family | type | inst | ..." ----------
SUFFIX = {'jr.', 'jr', 'iii', 'ii', 'sr.'}
for f, y in [('bc4147d7-NAS_2020_election.txt', 2020), ('de4318e5-NAS_2021_election.txt', 2021),
             ('23c6d3e8-NAS_2022_election.txt', 2022)]:
    for line in open(D + f, encoding='utf-8'):
        if ' | ' not in line or 'directory-entry' not in line:
            continue
        parts = [p.strip() for p in line.split(' | ')]
        name, typ = parts[0], parts[1]
        name_c = re.sub(r'\([^)]*\)', ' ', name)  # drop nicknames like (Kia)
        toks = name_c.split()
        while toks and toks[-1].lower() in SUFFIX:
            toks = toks[:-1]
        # particles belong to the family name
        fam_start = len(toks) - 1
        while fam_start > 1 and toks[fam_start - 1].lower() in {'van', 'de', 'der', 'den', 'von', 'di', 'da', 'del', 'la', 'le'}:
            fam_start -= 1
        family, given = ' '.join(toks[fam_start:]), ' '.join(toks[:fam_start])
        inst = parts[2] if len(parts) > 2 else ''
        dead = bool(re.search(r'\b(18|19|20)\d\d\s*-\s*\w+ \d{1,2}, (19|20)\d\d', inst))
        cat = 'international' if 'International' in typ else 'member'
        add('NAS', y, cat, family, given, '' if dead else inst, '',
            {'full_name_raw': name, 'deceased_listed': dead})

# ---------- Royal Society ----------
TITLE = r'(?:Professor|Prof|Dr|Sir|Dame|Mr|Ms|Mrs|Lord|Baroness|Lady)'
POST = re.compile(r'\s+(?:[A-Z][A-Za-z]*(?:SCi|Sci|Eng|RS|MS|BA|E|C|G|O|B)?)$')


def rs_parse(text, year):
    lines = [l.strip() for l in text.replace('\r', '').split('\n')]
    section = None
    for i, l in enumerate(lines):
        low = l.lower()
        if re.match(r'^(new )?fellows?( \d{4})?$', low) or low in ('fellowship',) or low.startswith('the full list'):
            section = 'fellow'
            continue
        if 'honorary fellow' in low and len(l) < 40:
            section = 'honorary'
            continue
        if 'foreign member' in low and len(l) < 40:
            section = 'foreign'
            continue
        if section is None:
            continue
        if not re.search(r'\b(FRS|ForMemRS)$', l):
            continue
        cat = section
        if l.endswith('ForMemRS'):
            cat = 'foreign'
        name = re.sub(r'\b(FRS|ForMemRS)$', '', l).strip()
        # strip further post-nominals (FMedSci, FREng, CBE, OBE, AC, OC, KBE, DBE, Kt, FBA, CB ...)
        while True:
            m = re.search(r'\s+([A-Z][A-Za-z]{0,6})$', name)
            if m and (m.group(1).isupper() or m.group(1) in {'FMedSci', 'FREng', 'Kt', 'FBA', 'DCMG', 'LG', 'DCB'}) and len(name.split()) > 2:
                name = name[:m.start()].strip()
            else:
                break
        name = re.sub(r'^' + TITLE + r'\.?\s+', '', name)
        name = re.sub(r'^(?:Dr|Sir|Dame|Professor)\s+', '', name)
        name = name.split(',')[0]  # "Dame Sue Black, Baroness Black of Strome"
        name = re.sub(r"^Professor Dr ", '', name)
        toks = name.split()
        fam_start = len(toks) - 1
        while fam_start > 1 and toks[fam_start - 1].lower() in {'van', 'de', 'der', 'von', 'di', 'da', 'del', 'la', 'le'}:
            fam_start -= 1
        aff = lines[i + 1] if i + 1 < len(lines) and lines[i + 1] else (lines[i + 2] if i + 2 < len(lines) else '')
        add('RoyalSociety', year, cat, ' '.join(toks[fam_start:]), ' '.join(toks[:fam_start]), aff, '',
            {'full_name_raw': l})


for f, y in [('83610cd6-RoyalSociety_2020_new_Fellows.txt', 2020), ('6035ec27-RoyalSociety_2021_new_Fellows.txt', 2021),
             ('576103a0-RoyalSociety_2022_new_Fellows.txt', 2022), ('f748ae64-RoyalSociety_2023_new_Fellows.txt', 2023),
             ('110632d9-RoyalSociety_2025_new_Fellows.txt', 2025)]:
    rs_parse(open(D + f, encoding='utf-8').read(), y)
t = html_text(glob.glob(D + '*Royal_Society.html')[0])
rs_parse(t, 2024)

# ---------- TWAS directory 2020-2025 ----------
METRIC = {
    'h_index': r'\bh[\s-]?index\b|\bh-factor\b|hirsch',
    'stanford_top2': r'stanford|top\s*2\s*%|top two per ?cent|world.?s top 2|elsevier.{0,40}(list|rank)',
    'citations': r'\bcitations?\b|\bcited\b',
    'any_ranking': r'highly cited researcher|clarivate|world ranking|ranked among|scival|research\.com',
}
txt = open(D + '11b6710d-TWAS_Fellows_elected_2020-2025_directory.txt', encoding='utf-8').read()
for block in re.split(r'\n(?=NAME: )', txt):
    if not block.startswith('NAME: '):
        continue
    g = dict(re.findall(r'^([A-Z]+): ?(.*)$', block, re.M))
    fam, _, given = g['NAME'].partition(',')
    bio = g.get('BIODATA', '')
    flags = {f'twas_{k}': bool(re.search(p, bio, re.I)) for k, p in METRIC.items()}
    flags['twas_metric_any'] = flags['twas_h_index'] or flags['twas_stanford_top2'] or flags['twas_citations'] or flags['twas_any_ranking']
    add('TWAS', int(g['ELECTED']), 'fellow', fam, given, g.get('INSTITUTION', ''), g.get('NATIONALITY', ''),
        {'residence': g.get('RESIDENCE', ''), 'section': g.get('SECTION', ''), 'bio_len': len(bio), **flags})

df = pd.DataFrame(rows)
import os
os.makedirs(OUT, exist_ok=True)
df.to_csv(OUT + 'criterion_elections.csv', index=False)
print(df.groupby(['source', 'year', 'category']).size().unstack(fill_value=0).to_string())
print('total rows', len(df))
