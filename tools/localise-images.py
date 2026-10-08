#!/usr/bin/env python3
"""Download every hotlinked product image into ./images/ and point index.html at the copies.

Run this on your own computer (the build sandbox can't reach the image hosts):

    python3 tools/localise-images.py            # download + rewrite index.html
    python3 tools/localise-images.py --dry-run  # just list what it would fetch

Needs only the Python standard library. Keeps a backup at index.html.bak.
Images that fail to download are left as remote links and listed at the end.
Check the licence/permission for each image before you publish self-hosted copies.
"""
import hashlib, os, re, sys, urllib.request, urllib.parse, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
OUT = os.path.join(ROOT, 'images')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
EXT = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/avif': '.avif', 'image/gif': '.gif', 'image/svg+xml': '.svg'}

html = open(PAGE, encoding='utf-8').read()
urls = list(dict.fromkeys(re.findall(r'<img class="card-img"[^>]*?src="(https?://[^"]+)"', html)))
hero = list(dict.fromkeys(re.findall(r'<span class="hs-img"><img src="(https?://[^"]+)"', html)))
urls = list(dict.fromkeys(urls + hero))
print(f'{len(urls)} remote images')
if '--dry-run' in sys.argv:
    print('\n'.join(urls)); sys.exit(0)

os.makedirs(OUT, exist_ok=True)
mapping, failed = {}, []
for u in urls:
    try:
        req = urllib.request.Request(urllib.parse.quote(u, safe=':/?&=%#+~@,;()!$*\'[]'), headers={'User-Agent': UA, 'Accept': 'image/*'})
        with urllib.request.urlopen(req, timeout=30) as r:
            data, ctype = r.read(), r.headers.get_content_type()
        ext = EXT.get(ctype) or os.path.splitext(urllib.parse.urlparse(u).path)[1] or '.img'
        name = hashlib.sha1(u.encode()).hexdigest()[:10] + ext
        open(os.path.join(OUT, name), 'wb').write(data)
        mapping[u] = 'images/' + name
        print('ok  ', u[:90])
    except Exception as e:
        failed.append((u, str(e)))
        print('FAIL', u[:90], e)

shutil.copy(PAGE, PAGE + '.bak')
for u, local in mapping.items():
    html = html.replace('src="%s"' % u, 'src="%s"' % local)
open(PAGE, 'w', encoding='utf-8').write(html)
print(f'\n{len(mapping)} downloaded, {len(failed)} failed. Backup: index.html.bak')
for u, e in failed: print('  still remote:', u, '-', e)
