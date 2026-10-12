#!/usr/bin/env python3
"""Assemble the publishable site: one HTML page with the engine's JS inlined, plus ac.wasm and data chunks."""
import hashlib, json, pathlib, shutil, sys
REL = pathlib.Path('/root/build/release')
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/site')
tpl = pathlib.Path('/root/build/site_template.html').read_text()
acjs = (REL / 'ac.js').read_text().replace('</script', '<\\/script')
wasm = (REL / 'ac.wasm').read_bytes()
ver = hashlib.sha1(wasm + acjs.encode()).hexdigest()[:12]
html = tpl.replace('/*__AC_JS__*/', acjs).replace('__WASM_SIZE__', str(len(wasm))).replace('__ENGINE_VERSION__', ver)
if OUT.exists():
    for f in OUT.iterdir():
        if f.is_file(): f.unlink()
        else: shutil.rmtree(f)
(OUT / 'data').mkdir(parents=True, exist_ok=True)
(OUT / 'assaultcube.html').write_text(html)
(OUT / 'ac.wasm').write_bytes(wasm)
idx = json.loads((REL / 'data' / 'index.json').read_text())
newchunks = []
for i, c in enumerate(idx['chunks']):
    name = f'ac-data-{i}.wasm'  # served type; contents are a gzip slice, read with fetch()
    shutil.copy(REL / 'data' / c, OUT / 'data' / name)
    newchunks.append(name)
idx['chunks'] = newchunks
(OUT / 'data' / 'index.json').write_text(json.dumps(idx, separators=(',', ':')))
print('html', len(html), 'bytes; wasm', len(wasm), '; engine version', ver)
for f in sorted(OUT.rglob('*')):
    if f.is_file(): print(f.relative_to(OUT), f.stat().st_size)
