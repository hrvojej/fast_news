#!/bin/bash
if [ $# -eq 0 ]; then
    echo "Usage: $0 /path/to/your/file"
    exit 1
fi

FILE_PATH="$1"
DIR_PATH=$(dirname "$FILE_PATH")

mkdir -p "$DIR_PATH"
rm -f "$FILE_PATH"
nano "$FILE_PATH"