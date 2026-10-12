#!/usr/bin/env python3
"""Pack AssaultCube game data into chunked blobs + a JSON index for the browser loader.

Output (in OUTDIR):
  data/index.json      [{"p": path, "o": offset, "s": size}, ...] plus chunk list
  data/pack.000 ...    raw concatenated file bytes, split into <=CHUNK bytes
"""
import json, os, sys, pathlib

ROOT = pathlib.Path(sys.argv[1])      # AssaultCube checkout
OUT = pathlib.Path(sys.argv[2]) / 'data'
CHUNK = 14 * 1024 * 1024
INCLUDE = ['packages', 'config', 'bot']
SKIP_SUFFIX = {'.txt~', '.bak', '.sh', '.bat'}
SKIP_DIRS = {'packages/maps/servermaps'}

# browser-specific tweaks to the game's own menu scripts (no networking, no window management, no quit)
WEB_PATCHES = {
    'config/menus.cfg': [
        ('''newmenu main
menuitem Multiplayer  [ showmenu multiplayer ]
menuitem Singleplayer [ showmenu singleplayer ]''', '''newmenu main
menuitem Singleplayer [ showmenu singleplayer ]'''),
        ('''menuitem "Quit AssaultCube"         quit''', '''menuitem "" -1
menuitem "\\f4Online multiplayer needs the desktop game (assault.cubers.net)" -1'''),
    ],
    'config/menus_settings.cfg': [
        ('''    scr_w $desktopw
    scr_h $desktoph
''', ''),
        ('''    menuitemradio "Fullscreen: " 0 1 "$__windowtype" [ "Yes" "No" ] [
        __windowtype = $arg1
        refreshcurmenudelayed // reset the screen width/height to desktop resolution whenever radio buttons are touched
    ]
    menuitemtextinput "Resolution / width: " "$scr_w" [ scr_w $arg1 ]
    menuitemtextinput "Resolution / height: " "$scr_h" [ scr_h $arg1 ]
''', ''),
        ('''    menuitem "\\f0\\t\\t\\t[ OK ]" [ 
        closecurmenu; 
        fullscreen (= $__windowtype 0)
        fullscreendesktop (= $__windowtype 0)
        resetgl 
        showmenu [auth setup]
    ]''', '''    menuitem "\\f0\\t\\t\\t[ OK ]" [ 
        closecurmenu; 
        showmenu singleplayer
    ]'''),
    ],
}

OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob('pack.*'):
    old.unlink()

entries, blob, total = [], bytearray(), 0
for top in INCLUDE:
    for dirpath, dirnames, filenames in os.walk(ROOT / top):
        rel_dir = os.path.relpath(dirpath, ROOT)
        dirnames[:] = sorted(d for d in dirnames if os.path.join(rel_dir, d) not in SKIP_DIRS)
        for fn in sorted(filenames):
            if any(fn.endswith(s) for s in SKIP_SUFFIX):
                continue
            rel = os.path.join(rel_dir, fn)
            data = (ROOT / rel).read_bytes()
            if rel in WEB_PATCHES:
                text = data.decode('latin-1')
                for old, new in WEB_PATCHES[rel]:
                    if old not in text:
                        raise SystemExit(f'web patch for {rel} did not match: {old[:60]!r}')
                    text = text.replace(old, new)
                data = text.encode('latin-1')
            entries.append({'p': rel, 'o': len(blob), 's': len(data)})
            blob += data

import gzip, hashlib
packed = gzip.compress(bytes(blob), compresslevel=9, mtime=0)
chunks = []
for i in range(0, len(packed), CHUNK):
    name = f'pack.{i // CHUNK:03d}'
    (OUT / name).write_bytes(packed[i:i + CHUNK])
    chunks.append(name)

index = {'total': len(blob), 'packed': len(packed), 'gzip': True, 'version': hashlib.sha1(packed).hexdigest()[:12], 'chunks': chunks, 'files': entries}
(OUT / 'index.json').write_text(json.dumps(index, separators=(',', ':')))
print(f'{len(entries)} files, {len(blob)/1e6:.1f} MB raw, {len(packed)/1e6:.1f} MB gzip in {len(chunks)} chunks')
