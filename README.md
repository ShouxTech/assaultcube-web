AssaultCube in the browser (WebAssembly build)
==============================================

Ported entirely by Claude Opus 5.5

Run it
------
The page has to be served over http (opening index.html directly from disk won't work,
browsers block file loading from file:// pages).

  macOS / Linux:  ./start.sh            then open http://localhost:8000
  Windows:        double-click start.bat

Both need Python 3. Without Python, any static server works from this folder, e.g.:
  npx serve .        (Node.js)        then open the address it prints

Click Deploy, enter a nickname, then pick a bot mode, skill, bot count and map.
Esc frees the mouse and opens the menu; click the game to aim again.

Files
-----
  index.html            page + engine glue (Emscripten JS inlined)
  ac.wasm               the AssaultCube client compiled to WebAssembly
  data/                 maps, textures, models, sounds and configs, gzip-packed in 3 parts
  build-scripts/        the patches and scripts used to build it from github.com/assaultcube/AC

Settings and your nickname are stored in the browser (IndexedDB) for the address you
serve it from, so keep using the same port. Online multiplayer is not available.
Game content is (c) the AssaultCube team and contributors; see the AC repository for licenses.
