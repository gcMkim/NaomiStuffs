#!/bin/sh

# (Put all ROMs into ../NaomiStuffs)
# Scan all .bin files in ../NaomiStuffs and create appropriate script link in current directory.

for i in ../NaomiStuffs/*.*; do
  BASENAME=$(basename "$i")
  GAMENAME=$(basename "$i" .bin)
  if [ ! -e "$GAMENAME" ]; then
    ln -v -s "naomi_LOAD.sh" "${GAMENAME}"
  fi
done
