#!/bin/bash
set -e

# Function to run disk analysis
run_disk_analysis() {
    echo "Running disk analysis..."
    python /app/misc_scripts/disk_analysis.py
    echo "Disk analysis complete."
}

# Parse command line arguments
DISK_CHECK=false
for arg in "$@"
do
    case $arg in
        --disk-check)
        DISK_CHECK=true
        shift # Remove --disk-check from processing
        ;;
    esac
done

# Run disk analysis if flag is provided
if [ "$DISK_CHECK" = true ] ; then
    run_disk_analysis
fi

DB_NAMES=("keyword_cache.db" "jobs.db")

if [ ! -f "/volume/db" ]; then
    mkdir -p /volume/db
fi

for DB_NAME in "${DB_NAMES[@]}"; do
  DB_PATH="/volume/db/$DB_NAME"
  if [ ! -f "$DB_PATH" ]; then
    echo "Local $DB_NAME not found. Attempting to restore from Tigris..."
    if litestream restore -if-replica-exists -o "$DB_PATH" "${BUCKET_NAME}/db/$DB_NAME"; then
      echo "Successfully restored $DB_NAME from Tigris."
    else
      echo "No $DB_NAME found in Tigris. Creating a new empty database."
      touch "$DB_PATH"
      sqlite3 "$DB_PATH" "VACUUM;"
    fi
  fi
done

# Run litestream with your application
exec litestream replicate -exec "python src/main.py --host 0.0.0.0 --port 8000"