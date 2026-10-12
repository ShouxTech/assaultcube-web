#!/usr/bin/env python3
"""Fix in Emscripten's legacy GL emulation: texture loads that use a texture matrix contain nested
parentheses, which the duplicate-load regex split in the wrong place, producing invalid GLSL."""
import pathlib
p = pathlib.Path('/root/emscripten/src/library_glemu.js')
s = p.read_text()
old1 = "var texLoadRegex = /(texture.*?\\(.*?\\))/g;"
old2 = "texLoadRegex = /(texture.*\\(.*\\))/g;"
new = "/(texture\\w*\\((?:[^()]|\\([^()]*\\))*\\))/g;"
if new in s:
    print('already patched')
else:
    assert old1 in s and old2 in s, 'pattern not found'
    s = s.replace(old1, "var texLoadRegex = " + new).replace(old2, "texLoadRegex = " + new)
    p.write_text(s)
    print('patched library_glemu.js')
