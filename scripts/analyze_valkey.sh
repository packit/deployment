#!/bin/bash
# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

# Script to analyze Valkey/Redis data and identify old/unnecessary data
# Usage: ./analyze_valkey.sh [namespace] [output-file]
#   namespace: OpenShift namespace (default: packit--prod)
#   output-file: Path to save report (default: valkey-analysis-report-TIMESTAMP.txt)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-packit--prod}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTPUT_FILE="${2:-valkey-analysis-report-${TIMESTAMP}.txt}"
COMPONENT="valkey"

# Progress indicator
progress() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if oc is available
if ! command -v oc &> /dev/null; then
    error "oc command not found. Please install OpenShift CLI."
    exit 1
fi

# Check if logged in to OpenShift
if ! oc whoami &> /dev/null; then
    error "Not logged in to OpenShift. Please run 'oc login' first."
    exit 1
fi

# Get Valkey pod name
progress "Finding Valkey pod in namespace: ${NAMESPACE}"
POD_NAME=$(oc get pod -n "${NAMESPACE}" -l component="${COMPONENT}" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    error "No Valkey pod found in namespace ${NAMESPACE}"
    exit 1
fi

success "Found pod: ${POD_NAME}"

# Initialize report
{
    echo "=========================================="
    echo "Valkey Data Analysis Report"
    echo "=========================================="
    echo "Generated: $(date)"
    echo "Namespace: ${NAMESPACE}"
    echo "Pod: ${POD_NAME}"
    echo "=========================================="
    echo ""
} > "$OUTPUT_FILE"

# Function to run valkey-cli command
valkey_cli() {
    oc exec -n "${NAMESPACE}" "${POD_NAME}" -- valkey-cli "$@" 2>/dev/null
}

# Function to append to report
report() {
    echo "$@" | tee -a "$OUTPUT_FILE"
}

# ==========================================
# 1. DISK USAGE ANALYSIS
# ==========================================
progress "Analyzing disk usage..."
report "=========================================="
report "1. DISK USAGE"
report "=========================================="

DISK_USAGE=$(oc exec -n "${NAMESPACE}" "${POD_NAME}" -- df -h /data 2>/dev/null)
report "$DISK_USAGE"
report ""

# Check RDB file size
RDB_SIZE=$(oc exec -n "${NAMESPACE}" "${POD_NAME}" -- sh -c 'du -sh /data/dump.rdb 2>/dev/null || echo "No dump.rdb found"')
report "RDB Persistence File Size:"
report "$RDB_SIZE"
report ""

# Extract disk usage percentage
DISK_USAGE_PERCENT=$(echo "$DISK_USAGE" | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE_PERCENT" -gt 80 ]; then
    warning "Disk usage is at ${DISK_USAGE_PERCENT}% - Consider cleanup or expansion"
fi

# ==========================================
# 2. MEMORY STATISTICS
# ==========================================
progress "Gathering memory statistics..."
report "=========================================="
report "2. MEMORY STATISTICS"
report "=========================================="

MEMORY_INFO=$(valkey_cli INFO MEMORY)
report "$MEMORY_INFO"
report ""

# Extract key metrics
USED_MEMORY=$(echo "$MEMORY_INFO" | grep "^used_memory_human:" | cut -d: -f2 | tr -d '\r')
USED_MEMORY_RSS=$(echo "$MEMORY_INFO" | grep "^used_memory_rss_human:" | cut -d: -f2 | tr -d '\r')
USED_MEMORY_PEAK=$(echo "$MEMORY_INFO" | grep "^used_memory_peak_human:" | cut -d: -f2 | tr -d '\r')

report "Key Memory Metrics:"
report "  - Used Memory: ${USED_MEMORY}"
report "  - RSS Memory: ${USED_MEMORY_RSS}"
report "  - Peak Memory: ${USED_MEMORY_PEAK}"
report ""

# ==========================================
# 3. KEYSPACE STATISTICS
# ==========================================
progress "Analyzing keyspace..."
report "=========================================="
report "3. KEYSPACE STATISTICS"
report "=========================================="

KEYSPACE_INFO=$(valkey_cli INFO KEYSPACE)
report "$KEYSPACE_INFO"
report ""

TOTAL_KEYS=$(valkey_cli DBSIZE)
report "Total Keys: ${TOTAL_KEYS}"
report ""

if [ "$TOTAL_KEYS" -eq 0 ]; then
    warning "No keys found in database!"
fi

# ==========================================
# 4. KEY PATTERN ANALYSIS
# ==========================================
progress "Scanning key patterns (this may take a moment)..."
report "=========================================="
report "4. KEY PATTERN ANALYSIS"
report "=========================================="

# Get sample keys to identify patterns
report "Sample of 20 random keys:"
for _ in {1..20}; do
    KEY=$(valkey_cli RANDOMKEY 2>/dev/null)
    if [ -n "$KEY" ]; then
        KEY_TYPE=$(valkey_cli TYPE "$KEY" 2>/dev/null | tr -d '\r')
        TTL=$(valkey_cli TTL "$KEY" 2>/dev/null | tr -d '\r')
        MEMORY=$(valkey_cli MEMORY USAGE "$KEY" 2>/dev/null | tr -d '\r')

        # Format TTL
        if [ "$TTL" = "-1" ]; then
            TTL_STATUS="NO_EXPIRY"
        elif [ "$TTL" = "-2" ]; then
            TTL_STATUS="NOT_FOUND"
        else
            TTL_STATUS="${TTL}s"
        fi

        report "  - ${KEY} | Type: ${KEY_TYPE} | TTL: ${TTL_STATUS} | Memory: ${MEMORY} bytes"
    fi
done
report ""

# Scan for common Celery patterns
progress "Scanning for Celery task metadata..."
report "=========================================="
report "5. CELERY TASK ANALYSIS"
report "=========================================="

# Count celery-task-meta keys
CELERY_META_COUNT=$(valkey_cli --scan --pattern "celery-task-meta-*" 2>/dev/null | wc -l)
report "Celery Task Metadata Keys: ${CELERY_META_COUNT}"

if [ "$CELERY_META_COUNT" -gt 0 ]; then
    # Sample some celery keys
    report ""
    report "Sample Celery Task Metadata (first 10):"
    valkey_cli --scan --pattern "celery-task-meta-*" 2>/dev/null | head -10 | while read -r key; do
        TTL=$(valkey_cli TTL "$key" 2>/dev/null | tr -d '\r')
        if [ "$TTL" = "-1" ]; then
            TTL_STATUS="PERMANENT (⚠️  NO EXPIRY)"
        elif [ "$TTL" = "-2" ]; then
            TTL_STATUS="KEY MISSING"
        else
            TTL_HOURS=$((TTL / 3600))
            TTL_STATUS="${TTL}s (${TTL_HOURS}h)"
        fi
        MEMORY=$(valkey_cli MEMORY USAGE "$key" 2>/dev/null | tr -d '\r')
        report "  - ${key}: TTL=${TTL_STATUS}, Memory=${MEMORY} bytes"
    done

    # Count keys without TTL
    NO_TTL_COUNT=0
    while IFS= read -r key; do
        TTL=$(valkey_cli TTL "$key" 2>/dev/null | tr -d '\r')
        if [ "$TTL" = "-1" ]; then
            ((NO_TTL_COUNT++)) || true
        fi
    done < <(valkey_cli --scan --pattern "celery-task-meta-*" 2>/dev/null | head -100)

    if [ "$NO_TTL_COUNT" -gt 0 ]; then
        warning "Found celery-task-meta keys without expiry! These will accumulate forever."
    fi
fi
report ""

# Check for other common patterns
progress "Scanning for other key patterns..."
for pattern in "celery-*" "_kombu.*" "unacked*" "*queue*"; do
    COUNT=$(valkey_cli --scan --pattern "$pattern" 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        report "Keys matching '${pattern}': ${COUNT}"
    fi
done
report ""

# ==========================================
# 6. LARGEST KEYS
# ==========================================
progress "Finding largest keys (this may take a while)..."
report "=========================================="
report "6. LARGEST KEYS BY TYPE"
report "=========================================="

BIGKEYS=$(valkey_cli --bigkeys 2>&1 | grep -v "^#" | grep -v "^$" || echo "No data")
report "$BIGKEYS"
report ""

# ==========================================
# 7. QUEUE ANALYSIS (for Celery)
# ==========================================
progress "Analyzing Celery queues..."
report "=========================================="
report "7. CELERY QUEUE ANALYSIS"
report "=========================================="

# Common Packit queue names (adjust based on your setup)
for queue in "celery" "short-running" "long-running"; do
    QUEUE_LEN=$(valkey_cli LLEN "$queue" 2>/dev/null | tr -d '\r')
    if [ -n "$QUEUE_LEN" ] && [ "$QUEUE_LEN" != "0" ]; then
        report "Queue '${queue}': ${QUEUE_LEN} tasks pending"
    fi
done
report ""

# ==========================================
# 8. TTL DISTRIBUTION ANALYSIS
# ==========================================
progress "Analyzing TTL distribution (sampling 100 keys)..."
report "=========================================="
report "8. TTL DISTRIBUTION (Sample of 100 keys)"
report "=========================================="

NO_EXPIRY=0
EXPIRED=0
WITH_TTL=0

while IFS= read -r key; do
    TTL=$(valkey_cli TTL "$key" 2>/dev/null | tr -d '\r')
    if [ "$TTL" = "-1" ]; then
        ((NO_EXPIRY++)) || true
    elif [ "$TTL" = "-2" ]; then
        ((EXPIRED++)) || true
    else
        ((WITH_TTL++)) || true
    fi
done < <(valkey_cli --scan 2>/dev/null | head -100)

report "Keys without expiry (TTL -1): ${NO_EXPIRY}"
report "Keys with TTL set: ${WITH_TTL}"
report "Keys not found (TTL -2): ${EXPIRED}"
report ""

if [ "$NO_EXPIRY" -gt 50 ]; then
    warning "More than 50% of sampled keys have no expiry! These will grow indefinitely."
fi

# ==========================================
# 9. PERSISTENCE CONFIGURATION
# ==========================================
progress "Checking persistence configuration..."
report "=========================================="
report "9. PERSISTENCE & CONFIGURATION"
report "=========================================="

CONFIG_MAXMEMORY=$(valkey_cli CONFIG GET maxmemory 2>/dev/null)
CONFIG_POLICY=$(valkey_cli CONFIG GET maxmemory-policy 2>/dev/null)
CONFIG_SAVE=$(valkey_cli CONFIG GET save 2>/dev/null)

report "Maxmemory Configuration:"
report "$CONFIG_MAXMEMORY"
report ""
report "Maxmemory Policy:"
report "$CONFIG_POLICY"
report ""
report "Save/Persistence Configuration:"
report "$CONFIG_SAVE"
report ""

MAXMEMORY_VALUE=$(echo "$CONFIG_MAXMEMORY" | tail -1 | tr -d '\r')
POLICY_VALUE=$(echo "$CONFIG_POLICY" | tail -1 | tr -d '\r')

if [ "$MAXMEMORY_VALUE" = "0" ]; then
    warning "No maxmemory limit set! Memory can grow unbounded."
fi

if [ "$POLICY_VALUE" = "noeviction" ]; then
    warning "maxmemory-policy is 'noeviction' - will cause errors when memory is full!"
fi

# ==========================================
# 10. RECOMMENDATIONS
# ==========================================
report "=========================================="
report "10. RECOMMENDATIONS"
report "=========================================="

if [ "$DISK_USAGE_PERCENT" -gt 80 ]; then
    report "⚠️  URGENT: Disk usage is at ${DISK_USAGE_PERCENT}%"
    report "   - Consider immediate cleanup or PVC expansion"
fi

if [ "$CELERY_META_COUNT" -gt 10000 ]; then
    report "⚠️  High number of Celery task metadata keys (${CELERY_META_COUNT})"
    report "   - Ensure Celery result_expires is set properly"
    report "   - Consider running: KEYS celery-task-meta-* | xargs DEL for old tasks"
fi

if [ "$MAXMEMORY_VALUE" = "0" ]; then
    report "⚠️  No memory limit configured"
    report "   - Set maxmemory to prevent OOM"
    report "   - Set maxmemory-policy (e.g., allkeys-lru or volatile-lru)"
fi

if [ "$NO_EXPIRY" -gt 50 ]; then
    report "⚠️  Many keys without TTL detected"
    report "   - Review key patterns and set appropriate expiry times"
fi

report ""
report "=========================================="
report "END OF REPORT"
report "=========================================="

success "Analysis complete! Report saved to: ${OUTPUT_FILE}"

# Display summary to console
echo ""
echo "=========================================="
echo "QUICK SUMMARY"
echo "=========================================="
echo "Disk Usage: ${DISK_USAGE_PERCENT}%"
echo "Total Keys: ${TOTAL_KEYS}"
echo "Used Memory: ${USED_MEMORY}"
echo "Celery Meta Keys: ${CELERY_META_COUNT}"
echo ""
echo "Full report: ${OUTPUT_FILE}"
echo "=========================================="
