#!/bin/bash

_crony_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_lock_file="$_crony_dir/.lock"

if test -e "$_lock_file"; then    
    echo "Lock file found. Trying removal ..."
    rm -f -- $_lock_file
    echo "Removed Lock file. No error reported."

else
    echo "Lock file not found."
fi