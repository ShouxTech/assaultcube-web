#!/bin/bash
# Compile the AssaultCube client to WebAssembly.
set -e
EMXX=/root/emscripten/em++
SRC=/root/build/acsrc/src
OBJ=/root/build/obj
DEPS=/root/build/deps
OUTDIR=${OUTDIR:-/root/build/web}
OPT=${OPT:--O2}
export EMCC_LOCAL_PORTS=sdl2=/root/deps/SDL-release-2.24.2
mkdir -p $OBJ/bot $OUTDIR
CXXFLAGS="$OPT -fsigned-char -fno-exceptions -Wno-everything -sUSE_SDL=2 -I$SRC -I$SRC/bot -I$SRC/../enet/include -I$DEPS/include"
FILES="crypto audiomanager autodownload client clientgame clients2c command console docs editing entities http log main menus oggstream openal packetqueue physics protocol rendercubes rendergl renderhud rendermodel renderparticles rendertext rndmap scoreboard serverms server serverbrowser shadow soundlocation soundscheduler stream texture tools water weapon wizard world worldio worldlight worldocull worldrender zip bot/bot bot/botmanager bot/bot_ai bot/bot_util bot/bot_waypoint bot/ac_bot bot/ac_bot_ai webshim acimm"
OBJS=()
for f in $FILES; do
  o=$OBJ/$f.o
  OBJS+=($o)
  if [ ! -f $o ] || [ $SRC/$f.cpp -nt $o ] || [ -n "$FORCE" ]; then
    extra=""; [ $f = rendermodel ] && extra="-fno-strict-aliasing"
    ( $EMXX $CXXFLAGS $extra -c $SRC/$f.cpp -o $o 2>&1 | grep -E "error" -A3 | head -30 ) &
    while [ $(jobs -r | wc -l) -ge 3 ]; do sleep 0.2; done
  fi
done
wait
for o in "${OBJS[@]}"; do [ -f $o ] || { echo "missing $o"; exit 1; }; done
echo "compiled; linking"
$EMXX $OPT -o $OUTDIR/ac.js "${OBJS[@]}" \
  -L$DEPS/lib -lSDL2_image -lvorbisfile -lvorbis -logg -lenet -lz -lopenal \
  -sUSE_SDL=2 -sLEGACY_GL_EMULATION=1 -sGL_UNSAFE_OPTS=0 -sGL_ENABLE_GET_PROC_ADDRESS=1 \
  -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=201326592 -sENVIRONMENT=web -sSTACK_SIZE=8388608 \
  -sFORCE_FILESYSTEM=1 -sINVOKE_RUN=0 -sEXIT_RUNTIME=0 \
  -sEXPORTED_RUNTIME_METHODS=FS,callMain,ENV,ccall,cwrap \
  -sEXPORTED_FUNCTIONS=_main \
  -lidbfs.js $LDEXTRA 2>&1 | grep -v "^ports:WARN" | head -40
ls -la $OUTDIR/ac.js $OUTDIR/ac.wasm
