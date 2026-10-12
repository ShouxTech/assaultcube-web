#!/bin/bash
# Build static wasm libraries for AssaultCube's C dependencies.
set -e
EMCC=/root/emscripten/emcc
EMAR=/root/emscripten/emar
DEPS=/root/deps
OUT=/root/build/deps
CFLAGS="-O2 -fno-exceptions"
mkdir -p $OUT/lib $OUT/include/ogg $OUT/include/vorbis
export EMCC_LOCAL_PORTS=sdl2=/root/deps/SDL-release-2.24.2

build_lib() { # name, srcdir, includes, files...
  local name=$1 dir=$2 inc=$3; shift 3
  local objdir=$OUT/obj/$name; mkdir -p $objdir
  local objs=()
  for f in "$@"; do
    local o=$objdir/$(basename ${f%.c}).o
    $EMCC $CFLAGS $inc -c $dir/$f -o $o &
    objs+=($o)
    # cap parallelism at 4
    while [ $(jobs -r | wc -l) -ge 4 ]; do sleep 0.1; done
  done
  wait
  rm -f $OUT/lib/lib$name.a
  $EMAR rcs $OUT/lib/lib$name.a "${objs[@]}"
  echo "built lib$name.a"
}

# zlib
build_lib z $DEPS/zlib "-DHAVE_UNISTD_H" adler32.c crc32.c deflate.c infback.c inffast.c inflate.c inftrees.c trees.c zutil.c compress.c uncompr.c gzclose.c gzlib.c gzread.c gzwrite.c
cp $DEPS/zlib/zlib.h $DEPS/zlib/zconf.h $OUT/include/

# ogg
cat > $OUT/include/ogg/config_types.h <<'EOF'
#ifndef __CONFIG_TYPES_H__
#define __CONFIG_TYPES_H__
#include <stdint.h>
#define INCLUDE_INTTYPES_H 1
#define INCLUDE_STDINT_H 1
#define INCLUDE_SYS_TYPES_H 1
typedef int16_t ogg_int16_t;
typedef uint16_t ogg_uint16_t;
typedef int32_t ogg_int32_t;
typedef uint32_t ogg_uint32_t;
typedef int64_t ogg_int64_t;
typedef uint64_t ogg_uint64_t;
#endif
EOF
cp $DEPS/ogg/include/ogg/ogg.h $DEPS/ogg/include/ogg/os_types.h $OUT/include/ogg/
build_lib ogg $DEPS/ogg/src "-I$OUT/include" bitwise.c framing.c

# vorbis + vorbisfile
cp $DEPS/vorbis/include/vorbis/*.h $OUT/include/vorbis/
VSRC="analysis.c bitrate.c block.c codebook.c envelope.c floor0.c floor1.c info.c lookup.c lpc.c lsp.c mapping0.c mdct.c psy.c registry.c res0.c sharedbook.c smallft.c synthesis.c window.c"
build_lib vorbis $DEPS/vorbis/lib "-I$OUT/include -I$DEPS/vorbis/lib" $VSRC
build_lib vorbisfile $DEPS/vorbis/lib "-I$OUT/include -I$DEPS/vorbis/lib" vorbisfile.c

# SDL_image with the bundled stb_image backend (PNG + JPG + TGA + BMP), no libpng/libjpeg needed
SDLI_FLAGS="-sUSE_SDL=2 -DLOAD_PNG -DLOAD_JPG -DLOAD_TGA -DLOAD_BMP -DUSE_STBIMAGE -I$DEPS/SDL_image"
build_lib SDL2_image $DEPS/SDL_image "$SDLI_FLAGS" IMG.c IMG_png.c IMG_jpg.c IMG_stb.c IMG_tga.c IMG_bmp.c IMG_WIC.c IMG_avif.c IMG_gif.c IMG_jxl.c IMG_lbm.c IMG_pcx.c IMG_pnm.c IMG_qoi.c IMG_svg.c IMG_tif.c IMG_webp.c IMG_xcf.c IMG_xpm.c IMG_xv.c IMG_xxx.c
cp $DEPS/SDL_image/SDL_image.h $OUT/include/

# enet (bundled with AssaultCube)
ENET=/root/src/ac/source/enet
build_lib enet $ENET "-I$ENET/include -DHAS_SOCKLEN_T=1 -DHAS_FCNTL=1 -DHAS_POLL=1 -DHAS_GETADDRINFO=1 -DHAS_GETNAMEINFO=1 -DHAS_INET_PTON=1 -DHAS_INET_NTOP=1 -DHAS_MSGHDR_FLAGS=1" callbacks.c compress.c host.c list.c packet.c peer.c protocol.c unix.c
ls -la $OUT/lib
