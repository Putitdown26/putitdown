#!/usr/bin/env python3
"""Tag every translatable string in index.html and write i18n/en.json.

Run this after you change any English copy:

    python3 tools/i18n-build.py

What it does
  * adds data-i18n="key" to each element whose text should be translated
    (and data-i18n-attr="aria-label:key;placeholder:key" for translated attributes)
  * writes i18n/en.json with key -> English text, plus the strings the page script uses
  * writes i18n/_changed.txt listing keys that are new or whose English text changed,
    so you know which translations to redo

Keys are made from the first few words plus a short hash of the full text, so unchanged
copy keeps its key (and its existing translations) and edited copy gets a fresh key.
Product names, prices and the logo are never translated.
"""
import hashlib, json, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
OUT = os.path.join(ROOT, 'i18n')

SKIP_CLASSES = {'card-title', 'hs-name', 'price-gbp', 'price-us', 'logo', 'no-i18n', 'card-more-btn', 'yt-wrap'}
SKIP_TAGS = {'script', 'style', 'svg', 'iframe', 'select', 'noscript', 'head', 'title'}
VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'area', 'base', 'col', 'embed', 'param', 'track', 'wbr', 'path', 'circle', 'rect', 'use'}
ATTRS = ('aria-label', 'placeholder', 'title')

# Strings the page script builds itself. {a}, {b}, {name} are filled in at run time.
JS_STRINGS = {
    'js.more': 'More ↓',
    'js.less': 'Less ↑',
    'js.copy': 'Copy link',
    'js.copied': 'Copied!',
    'js.count': '{a} of {b}',
    'js.swipe': 'Swipe → {a} of {b}',
    'js.region': '{name} products, scroll sideways',
    'js.prev': 'Previous products',
    'js.next': 'Next products',
    'js.language': 'Language',
}

html_text = open(PAGE, encoding='utf-8').read()
# start clean: remove any tags from an earlier run
html_text = re.sub(r' data-i18n(?:-attr)?="[^"]*"', '', html_text)

line_starts = [0]
for m in re.finditer('\n', html_text):
    line_starts.append(m.end())
def abs_pos(lineno, col): return line_starts[lineno - 1] + col


class El:
    __slots__ = ('tag', 'attrs', 'start', 'open_end', 'close_start', 'end', 'direct', 'skip', 'in_body')
    def __init__(self, tag, attrs, start, open_end, skip, in_body):
        self.tag, self.attrs, self.start, self.open_end = tag, dict(attrs), start, open_end
        self.close_start = self.end = None
        self.direct = ''
        self.skip, self.in_body = skip, in_body


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack, self.els, self.body = [], [], False
    def handle_starttag(self, tag, attrs):
        st = self.get_starttag_text()
        pos = abs_pos(*self.getpos())
        if tag == 'body': self.body = True
        parent_skip = self.stack[-1].skip if self.stack else False
        cls = set((dict(attrs).get('class') or '').split())
        skip = parent_skip or tag in SKIP_TAGS or bool(cls & SKIP_CLASSES) or 'data-no-i18n' in dict(attrs)
        e = El(tag, attrs, pos, pos + len(st), skip, self.body)
        self.els.append(e)
        if tag in VOID or st.endswith('/>'):
            e.close_start = e.end = e.open_end
        else:
            self.stack.append(e)
    def handle_endtag(self, tag):
        pos = abs_pos(*self.getpos())
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                for e in self.stack[i:]:
                    e.close_start = pos
                    e.end = pos + len(tag) + 3
                del self.stack[i:]
                return
    def handle_data(self, data):
        if self.stack: self.stack[-1].direct += data
    def handle_entityref(self, name):
        if self.stack: self.stack[-1].direct += '&' + name + ';'
    def handle_charref(self, name):
        if self.stack: self.stack[-1].direct += '&#' + name + ';'

p = P(); p.feed(html_text); p.close()

def norm(t): return re.sub(r'\s+', ' ', t).strip()
def plain(t): return re.sub(r'&[a-z#0-9]+;', ' ', re.sub(r'<[^>]+>', ' ', t))
def make_key(prefix, raw):
    words = re.findall(r'[a-z0-9]+', plain(raw).lower())[:4]
    return prefix + '-'.join(words)[:28].strip('-') + '-' + hashlib.sha1(raw.encode()).hexdigest()[:5]

strings, inserts, covered = {}, [], 0
for e in p.els:
    if not e.in_body or e.close_start is None: continue
    attr_pairs = []
    if not e.skip or e.tag == 'a':   # logo link still carries an aria-label
        for a in ATTRS:
            v = e.attrs.get(a)
            if v and re.search(r'[A-Za-z]{3,}', v) and e.tag != 'iframe':
                k = make_key('a.', norm(v)); strings[k] = norm(v); attr_pairs.append(f'{a}:{k}')
    unit_key = None
    if not e.skip and e.start >= covered and re.search(r'[^\W\d_]{2,}', plain(e.direct)):
        inner = norm(html_text[e.open_end:e.close_start])
        if inner:
            unit_key = make_key('', inner); strings[unit_key] = inner
            covered = e.end
    elif e.skip and e.start >= covered and any(c in (e.attrs.get('class') or '') for c in SKIP_CLASSES):
        covered = max(covered, e.end or 0)
    if unit_key or attr_pairs:
        ins = ''
        if unit_key: ins += f' data-i18n="{unit_key}"'
        if attr_pairs: ins += f' data-i18n-attr="{";".join(attr_pairs)}"'
        inserts.append((e.start + 1 + len(e.tag), ins))

for pos, ins in sorted(inserts, reverse=True):
    html_text = html_text[:pos] + ins + html_text[pos:]
open(PAGE, 'w', encoding='utf-8').write(html_text)

# page <title> and description
t = re.search(r'<title>(.*?)</title>', html_text, re.S).group(1).strip()
d = re.search(r'<meta name="description" content="([^"]*)"', html_text).group(1)
strings['meta.title'] = t
strings['meta.description'] = d
strings.update(JS_STRINGS)

os.makedirs(OUT, exist_ok=True)
old = {}
en_path = os.path.join(OUT, 'en.json')
if os.path.exists(en_path): old = json.load(open(en_path, encoding='utf-8'))
changed = [k for k, v in strings.items() if old.get(k) != v]
json.dump(strings, open(en_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(OUT, '_changed.txt'), 'w').write('\n'.join(changed))
words = sum(len(plain(v).split()) for v in strings.values())
print(f'{len(strings)} strings, ~{words} words; {len(changed)} new or changed')
