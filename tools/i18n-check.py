#!/usr/bin/env python3
"""Check translation files against i18n/en.json.

    python3 tools/i18n-check.py            # all languages
    python3 tools/i18n-check.py de fr      # just these

Errors: invalid JSON, missing or extra keys, empty values, HTML tags or
{placeholders} that differ from the English. Warnings: values identical to English.
"""
import json, os, re, sys
from collections import Counter
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'i18n')
en = json.load(open(os.path.join(D, 'en.json'), encoding='utf-8'))
codes = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(D) if f.endswith('.json') and f != 'en.json')
tag = re.compile(r'<[^>]+>'); ph = re.compile(r'\{[a-z]+\}')
bad = 0
for c in codes:
    path = os.path.join(D, c + '.json')
    if not os.path.exists(path): print(f'{c}: MISSING FILE'); bad += 1; continue
    try: tr = json.load(open(path, encoding='utf-8'))
    except Exception as e: print(f'{c}: INVALID JSON {e}'); bad += 1; continue
    errs, same = [], 0
    for k in en.keys() - tr.keys(): errs.append(f'missing key {k}')
    for k in tr.keys() - en.keys(): errs.append(f'extra key {k}')
    for k, v in en.items():
        t = tr.get(k)
        if t is None: continue
        if not isinstance(t, str) or not t.strip(): errs.append(f'empty {k}'); continue
        if Counter(x.replace(' />', '>').replace('/>', '>') for x in tag.findall(t)) != Counter(x.replace(' />', '>').replace('/>', '>') for x in tag.findall(v)):
            errs.append(f'tags differ {k}: {tag.findall(v)} vs {tag.findall(t)}')
        if Counter(ph.findall(t)) != Counter(ph.findall(v)): errs.append(f'placeholders differ {k}')
        if t == v and len(re.findall(r'[A-Za-z]{4,}', v)) > 1: same += 1
    print(f'{c}: {len(errs)} errors, {same} identical to English' + ('' if not errs else '\n  ' + '\n  '.join(errs[:12])))
    bad += bool(errs)
sys.exit(1 if bad else 0)
