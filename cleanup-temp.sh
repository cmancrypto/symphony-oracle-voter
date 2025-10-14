#!/bin/bash
# Comprehensive cleanup for temp files and caches
# This script is copied to /usr/local/bin/ during Docker build

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting cleanup..."

# Function to get directory size in MB
get_size_mb() {
    du -sm "$1" 2>/dev/null | awk '{print $1}'
}

# 1. AGGRESSIVE: Clean up ANY symphonyd temp directories in /tmp (both root and /tmp/symphony)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning symphonyd temp directories..."

# Count and remove from /tmp root
SYMPHONYD_DIRS_ROOT=$(find /tmp -maxdepth 1 -type d -name "symphonyd*" 2>/dev/null | wc -l)

# Count and remove from /tmp/symphony
SYMPHONYD_DIRS_SYMPHONY=0
if [ -d "/tmp/symphony" ]; then
    SYMPHONYD_DIRS_SYMPHONY=$(find /tmp/symphony -maxdepth 1 -type d -name "symphonyd*" 2>/dev/null | wc -l)
fi

SYMPHONYD_DIRS=$((SYMPHONYD_DIRS_ROOT + SYMPHONYD_DIRS_SYMPHONY))

if [ "$SYMPHONYD_DIRS" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found $SYMPHONYD_DIRS symphonyd temp directories (root: $SYMPHONYD_DIRS_ROOT, symphony: $SYMPHONYD_DIRS_SYMPHONY) - removing ALL"
    
    # Remove from /tmp root
    find /tmp -maxdepth 1 -type d -name "symphonyd*" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove from /tmp/symphony
    if [ -d "/tmp/symphony" ]; then
        find /tmp/symphony -maxdepth 1 -type d -name "symphonyd*" -exec rm -rf {} + 2>/dev/null || true
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Removed symphonyd temp directories"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No symphonyd temp directories found (GOOD!)"
fi

# 2. Count temp files before general cleanup
BEFORE_COUNT=$(find /tmp -type f 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Total temp files before cleanup: $BEFORE_COUNT"

# 3. Clean up old temp files (older than 1 day)
find /tmp -type f -mtime +1 -delete 2>/dev/null || true

# 4. Clean up empty directories
find /tmp -type d -empty -delete 2>/dev/null || true

# 5. Count after cleanup
AFTER_COUNT=$(find /tmp -type f 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Total temp files after cleanup: $AFTER_COUNT"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up $((BEFORE_COUNT - AFTER_COUNT)) temp files"

# 6. Check WASM cache size and clean if needed
if [ -d "/symphony/.cache" ]; then
    CACHE_SIZE=$(get_size_mb "/symphony/.cache")
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WASM cache size: ${CACHE_SIZE}MB"
    
    # If cache is over 200MB, clean older items
    if [ "$CACHE_SIZE" -gt 200 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: Cache size ${CACHE_SIZE}MB exceeds 200MB - cleaning old cache items"
        find /symphony/.cache -type f -mtime +7 -delete 2>/dev/null || true
        CACHE_SIZE_AFTER=$(get_size_mb "/symphony/.cache")
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cache size after cleanup: ${CACHE_SIZE_AFTER}MB"
    fi
fi

# 7. Final status report
SYMPHONYD_REMAINING_ROOT=$(find /tmp -maxdepth 1 -type d -name "symphonyd*" 2>/dev/null | wc -l)
SYMPHONYD_REMAINING_SYMPHONY=0
if [ -d "/tmp/symphony" ]; then
    SYMPHONYD_REMAINING_SYMPHONY=$(find /tmp/symphony -maxdepth 1 -type d -name "symphonyd*" 2>/dev/null | wc -l)
fi
SYMPHONYD_REMAINING=$((SYMPHONYD_REMAINING_ROOT + SYMPHONYD_REMAINING_SYMPHONY))

if [ "$SYMPHONYD_REMAINING" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $SYMPHONYD_REMAINING symphonyd temp directories STILL present! (root: $SYMPHONYD_REMAINING_ROOT, symphony: $SYMPHONYD_REMAINING_SYMPHONY)"
elif [ "$AFTER_COUNT" -gt 1000 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  WARNING: $AFTER_COUNT temp files remaining (threshold: 1000)"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Cleanup complete - system healthy"
fi
