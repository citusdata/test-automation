#!/bin/bash

set -euo pipefail

for f in $(git ls-tree -r HEAD --name-only); do
    # only process files with extensions sh, py or azuredeploy
    if [ "$f" != "${f%.sh}" ]  ||
        [ "$f" != "${f%.py}" ] ||
        [ "$f" != "${f%.azuredeploy%}" ]
    then
        # Trim trailing whitespace
        sed -e 's/[[:space:]]*$//' -i "./$f"
        # Add final newline if not there
        if [ -n "$(tail -c1 "$f")" ]; then
            echo >> "$f"
        fi
    fi
done
