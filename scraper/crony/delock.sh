#!/bin/bash

_crony_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_lock_file="$_crony_dir/.lock"

if test -e "$_lock_file"; then
    echo "Trying to remove Lock file."
    rm -f -- $_lock_file
else
    echo "Lock file not found."
fi