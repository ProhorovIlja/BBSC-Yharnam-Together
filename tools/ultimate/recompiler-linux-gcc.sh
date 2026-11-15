#!/bin/sh
# GPL-2.0-or-later. Linux research adapter for bloodborne-native/bbcpu and bloodborne-recomp.
# Their source remains external and unchanged. This does not enable a game runtime backend.
if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    printf '%s\n' 'This adapter is verified only on Linux x86-64.' >&2
    exit 1
fi
exec "${BB_RECOMP_GCC:-gcc}" -D_GNU_SOURCE -DBB_HAVE_BBCPU=1 -DMAP_JIT=0 \
    -fno-strict-aliasing "$@" -Wno-error=sign-compare -lm -ldl -latomic -pthread
