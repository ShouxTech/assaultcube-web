# AssaultCube in the browser (WebAssembly build)

Ported entirely by Claude Opus 5.5.

## Run it

The page has to be served over HTTP. Opening `index.html` directly from disk won't work, because browsers block file loading from `file://` pages.

**Windows**

Double-click `start.bat`.

**macOS / Linux**

```sh
./start.sh
```

Then open <http://localhost:8000>.

Both need Python 3. Without Python, any static server works from this folder, for example with Node.js:

```sh
npx serve .
```

Then open the address it prints.

## Playing

1. Click **Deploy** and enter a nickname.
2. Pick a bot mode, skill, bot count and map.

Press <kbd>Esc</kbd> to free the mouse and open the menu. Click the game to aim again.

## Files

| Path | Description |
| --- | --- |
| `index.html` | Page and engine glue (Emscripten JS inlined) |
| `ac.wasm` | The AssaultCube client compiled to WebAssembly |
| `data/` | Maps, textures, models, sounds and configs, gzip-packed in 3 parts |
| `build-scripts/` | The patches and scripts used to build it from [assaultcube/AC](https://github.com/assaultcube/AC) |

## Notes

- Settings and your nickname are stored in the browser (IndexedDB) for the address you serve it from, so keep using the same port.
- Online multiplayer is not available.

## License

Game content is © the AssaultCube team and contributors. See the [AC repository](https://github.com/assaultcube/AC) for licenses.
