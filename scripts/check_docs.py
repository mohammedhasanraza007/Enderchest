#!/usr/bin/env python3
"""Consistency checker for the Enderchest doc pack. Run from anywhere: python scripts/check_docs.py
Checks: section references, decision ids, repo paths, stale wording, read-when headers,
and that every endpoint named in PAGES.md / specs / DATA_SAFETY.md exists in API.md (and vice versa, as warnings)."""
import re, os, sys, glob, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
files = sorted(glob.glob(f'{ROOT}/**/*.md', recursive=True))
rel = lambda f: os.path.relpath(f, ROOT).replace('\\', '/')
base = os.path.basename
read = lambda f: open(f, encoding='utf-8').read()
errors, warnings = [], []

# 1 section references -------------------------------------------------------
heads = collections.defaultdict(set)
for f in files:
    for line in read(f).split('\n'):
        m = re.match(r'^#{1,4}\s+(\d+(?:\.\d+)*)[.)]?\s', line) or re.match(r'^#{1,4}\s+([A-Z])\.\s', line)
        if m: heads[base(f)].add(m.group(1))
names = ['CLAUDE','DESIGN','DATA_SAFETY','PROCESS','PROJECT_PLAN','DECISIONS','MISTAKES_TO_AVOID','PAGES','API','DATA_MODEL','ARCHITECTURE']
pat = re.compile(r'`?(?:docs/)?(' + '|'.join(names) + r')\.md`?[ ,]*(?:section|sections|§)?\s*(\d+(?:\.\d+)*|[A-Z](?![-\w]))')
for f in files:
    if 'history' in f or 'PLAN_REVIEW' in f: continue
    txt = read(f)
    for m in pat.finditer(txt):
        tgt, sec = m.group(1) + '.md', m.group(2)
        if m.group(0).split('.md')[1].strip(' `,') == '' : continue
        if not re.search(r'(section|sections|§)\s*' + re.escape(sec), m.group(0)) and not re.search(r'\.md`?\s+' + re.escape(sec) + r'\b', m.group(0)):
            continue
        if tgt in {base(x) for x in files} and sec not in heads[tgt]:
            errors.append(f'{rel(f)}:{txt[:m.start()].count(chr(10))+1}: {tgt} has no section {sec}')

# 2 decision / open-question ids ------------------------------------------------
dec = read(f'{ROOT}/docs/DECISIONS.md')
ids = set(re.findall(r'\b([DO]-\d{3})\b', dec))
for f in files:
    if 'history' in f or 'PLAN_REVIEW' in f: continue
    for i, line in enumerate(read(f).split('\n'), 1):
        for m in re.finditer(r'\b([DO]-\d{3})\b', line):
            if m.group(1) not in ids: errors.append(f'{rel(f)}:{i}: {m.group(1)} not in DECISIONS.md')

# 3 backticked repo paths ---------------------------------------------------------
future_ok = ('tests/e2e/', 'docs/reviews/phase-', 'docs/specs/frontend', 'docs/logs/raw/phase-', 'tests/fixtures/private/', 'frontend/', 'backend/', 'scripts/export_openapi')
for f in files:
    if 'history' in f: continue
    for i, line in enumerate(read(f).split('\n'), 1):
        for m in re.finditer(r'`((?:docs|assets|\.claude|tests|scripts)/[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+)`', line):
            p = m.group(1)
            if any(x in p for x in ('<', '*', 'phase-N')) or p.startswith(future_ok): continue
            if not os.path.exists(os.path.join(ROOT, p)): errors.append(f'{rel(f)}:{i}: path {p} does not exist')

# 4 stale wording -------------------------------------------------------------------
stale = [r'\bArchitect\b', r'\(9\.3\)', r'laptop and PC', r'Phase 8 (is )?locked', r'Phase Verification Gate in `CLAUDE\.md`', r'predictive maintenance(?! here)(?!\))']
for f in files:
    if 'history' in f or 'PLAN_REVIEW' in f or base(f) in ('MISTAKES_TO_AVOID.md',): continue
    for i, line in enumerate(read(f).split('\n'), 1):
        for s in stale:
            if re.search(s, line, re.I if 'predictive' in s else 0) and 'not "predictive' not in line and 'not predictive' not in line and 'call it predictive' not in line:
                errors.append(f'{rel(f)}:{i}: stale wording /{s}/')

# 5 read-when headers on big docs -------------------------------------------------------
for n in ['API','PAGES','DATA_MODEL','DATA_SAFETY','ARCHITECTURE','DESIGN','PROCESS','PROJECT_PLAN','MISTAKES_TO_AVOID','DECISIONS']:
    if '**Read when:**' not in read(f'{ROOT}/docs/{n}.md')[:2500]: errors.append(f'docs/{n}.md: missing Read-when header')
for f in glob.glob(f'{ROOT}/docs/specs/phase-*.md'):
    if '**Read list' not in read(f)[:1200]: errors.append(f'{rel(f)}: missing Read list')

# 5b page ids P-xx used anywhere must exist as headings in PAGES.md
pages = read(f'{ROOT}/docs/PAGES.md')
page_ids = set(re.findall(r'^## (P-\d\d)\b', pages, re.M))
for f in files:
    if 'history' in f or 'PLAN_REVIEW' in f: continue
    for i, line in enumerate(read(f).split('\n'), 1):
        for m in re.finditer(r'\b(P-\d\d)\b', line):
            if m.group(1) not in page_ids: errors.append(f'{rel(f)}:{i}: page id {m.group(1)} is not a heading in PAGES.md')

# 6 endpoints ---------------------------------------------------------------------------------
norm = lambda m, p: m + ' ' + re.sub(r'\{[^}]*\}', '{}', p.split('?')[0].rstrip('/'))
api = set()
for line in read(f'{ROOT}/docs/API.md').split('\n'):
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(c) >= 4 and c[1] in ('GET','POST','PUT','PATCH','DELETE') and c[2].startswith('/'):
        api.add(norm(c[1], c[2] if c[2].startswith('/health') else '/api/v1' + c[2]))
used = set()
for f in [f'{ROOT}/docs/PAGES.md', f'{ROOT}/docs/DATA_SAFETY.md', f'{ROOT}/docs/ARCHITECTURE.md'] + glob.glob(f'{ROOT}/docs/specs/*.md') + [f'{ROOT}/CLAUDE.md']:
    for i, line in enumerate(read(f).split('\n'), 1):
        for m in re.finditer(r'`(GET|POST|PUT|PATCH|DELETE) (/[^`\s]*)`', line):
            e = norm(m.group(1), m.group(2)); used.add(e)
            if e not in api: errors.append(f'{rel(f)}:{i}: endpoint `{m.group(1)} {m.group(2)}` is not in API.md')
orph = sorted(api - used)
for e in orph: warnings.append(f'API.md endpoint not referenced by any page or spec: {e}')

print(f'{len(files)} md files, {len(api)} endpoints in API.md, {len(used)} referenced')
for w in warnings: print('WARN ', w)
for e in errors: print('ERROR', e)
print(f'\n{len(errors)} errors, {len(warnings)} warnings')
sys.exit(1 if errors else 0)
