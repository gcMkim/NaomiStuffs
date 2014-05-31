#!/bin/bash

PYTHON=python2
GAMENAME=$(basename "$0")
#NAOMI_HOME=/mnt/naomi
NAOMI_HOME=/home/nasuser1/naomi

echo ${PYTHON} ${NAOMI_HOME}/naomi_boot.py "${NAOMI_HOME}/NaomiStuffs/${GAMENAME}.bin"
${PYTHON} ${NAOMI_HOME}/naomi_boot.py "${NAOMI_HOME}/NaomiStuffs/${GAMENAME}.bin"
