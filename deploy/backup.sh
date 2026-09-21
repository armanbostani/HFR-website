#!/usr/bin/env bash
# Nightly backup: consistent SQLite snapshot + avatars + applicant CVs.
# Keeps 30 days locally in /srv/hfr-website/backups. Copy that folder
# off the server too (rclone to the society Google Drive is the easy route).
set -euo pipefail

ROOT=/srv/hfr-website
DEST=$ROOT/backups
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p "$DEST"

# .backup takes a consistent copy even while the site is running
sqlite3 "$ROOT/app/db.sqlite3" ".backup '$DEST/db_$STAMP.sqlite3'"
tar -czf "$DEST/files_$STAMP.tar.gz" -C "$ROOT" media private_media

find "$DEST" -type f -mtime +30 -delete
echo "backup written: $DEST/db_$STAMP.sqlite3 and files_$STAMP.tar.gz"
