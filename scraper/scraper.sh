#!/bin/bash

echo ">>>>>>>>>>> JOB STARTED >>>>>>>>>>>"

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
    echo "Another script is probably running or did not finish as expected." # >> "$_logs_file"
    echo "The lock file will be removed on next boot. It can also be removed manually." # >> "$_logs_file"
else
    echo "Lock file $_lock_file_short was not found." >> "$_logs_file"
    touch $_lock_file
    DJANGO_DIR="$SCRIPT_DIR/../"

    cd $DJANGO_DIR
    source $DJANGO_DIR/.venv/bin/activate
    python scraper/worker.py "$@" >> "$_logs_file"
    deactivate

    # If operating from a remote machine, transfer files to the server.
    # This is checked by the existence of _local_file (which is created only on the server, not on remote machines)
    _local_file="$_crony_dir/.local"
    if ! test -e "$_local_file"; then
        # rsync-dce and rsync-logs are aliases to rsync commands like 
        # `rsync -av --update -e 'ssh [-p xxxx]' <full-path-to-local-dce-folder/> <user>@emarches.com:<full-path-to-dce-folder>' 
        # `rsync -av --update -e 'ssh [-p xxxx]' <full-path-to-local-logs-folder/> <user>@emarches.com:<full-path-to-logs-folder>' 
        # Note: pre-established SSH tunnel is required
        echo "Transferring DCE files ..."
        bash -ic "rsync-dce"
        echo "Transferring logs files ..."
        bash -ic "rsync-logs"
    fi

    echo "Script finished executing. See logs and system journal for details." >> "$_logs_file"
    if test -e "$_lock_file"; then
        echo "Script finished. Trying to remove Lock file." >> "$_logs_file"
        rm -f -- $_lock_file
        echo "Removed Lock file." >> "$_logs_file"
    fi
fi

echo "<<<<<<<<< JOB FINISHED <<<<<<<<<"


