#!/bin/bash

echo ">>>>>>>>>>>>JOB>STARTED>>>>>>>>>>>>"

# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" && cd ..)" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_now=$(date +"%Y%m%d-%H%M%S")
_logs_dir="$SCRIPT_DIR/logs"
_logs_file="$_logs_dir/scraper-$_now.log"
_crony_dir="$SCRIPT_DIR/crony"
_lock_file="$_crony_dir/.lock"

if ! [ -d "$_crony_dir" ]; then
    mkdir -p $_crony_dir
fi

if ! test -e "$_logs_file"; then
    mkdir -p $_logs_dir && touch $_logs_file
fi

_lock_file_short=".lock"

if test -e "$_lock_file"; then
    echo "Execution prevented by a Lock file: $_lock_file_short" >> "$_logs_file"
else
    echo "Lock file $_lock_file_short was not found." >> "$_logs_file"
    touch $_lock_file
    DJANGO_DIR="$SCRIPT_DIR/../"

    echo "Working directory: $DJANGO_DIR" >> "$_logs_file"

    cd $DJANGO_DIR
    echo "Current directory: $(pwd)" >> "$_logs_file"

    source $DJANGO_DIR/.venv/bin/activate
    python scraper/worker.py "$@" >> "$_logs_file"

    # If operating from a remote machine, transfer files to the server.
    # This is checked by the existence of _local_file (which is created only on the server, not on remote machines)
    _local_file="$_crony_dir/.local"
    if ! test -e "$_local_file"; then
        # rsync-dce and rsync-logs are aliases to rsync commands like 
        # `rsync -av --update -e 'ssh [-p xxxx]' <full-path-to-local-dce-folder/> <user>@<remote-server>:<full-path-to-server-dce-folder>' 
        # `rsync -av --update -e 'ssh [-p xxxx]' <full-path-to-local-logs-folder/> <user>@<remote-server>:<full-path-to-server-logs-folder>' 
        # Note: pre-configured SSH tunnel is required
        echo "Transferring DCE files ..."  >> "$_logs_file"
        bash -ic "rsync-dce" >> "$_logs_file"
        echo "Transferring logs files ..." >> "$_logs_file"
        bash -ic "rsync-logs" >> "$_logs_file"
    fi

    echo "Script finished executing. See logs and system journal for details." >> "$_logs_file"
    if test -e "$_lock_file"; then
        echo "Script finished. Trying to remove Lock file." >> "$_logs_file"
        rm -f -- $_lock_file
        echo "Removed Lock file." >> "$_logs_file"
    fi
fi

echo "<<<<<<<<<JOB<FINISHED<<<<<<<<<"


