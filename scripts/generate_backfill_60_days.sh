#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/wb_mock_api"
RUNTIME_DIR="${PROJECT_DIR}/runtime_backfill"
LIVE_DIR="/var/www/html"
BACKFILL_ROOT="${LIVE_DIR}/backfill"

DAYS="${1:-60}"
END_DATE="${2:-2026-07-03}"

mkdir -p "$BACKFILL_ROOT"

echo "WB mock backfill started"
echo "days: $DAYS"
echo "end date: $END_DATE"
echo "live dir: $LIVE_DIR"
echo "backfill root: $BACKFILL_ROOT"

rm -rf "$RUNTIME_DIR"
mkdir -p "$RUNTIME_DIR"

cp "${PROJECT_DIR}/specs/"*.yaml "$RUNTIME_DIR/"
cp "${PROJECT_DIR}/scripts/"*.py "$RUNTIME_DIR/"

for OFFSET in $(seq "$((DAYS - 1))" -1 0); do
    DAY="$(python3 - <<PY
from datetime import date, timedelta
end = date.fromisoformat("$END_DATE")
print((end - timedelta(days=$OFFSET)).isoformat())
PY
)"

    OUT_DIR="${BACKFILL_ROOT}/${DAY}"

    echo
    echo "=== generating day: ${DAY} ==="

    rm -rf "$OUT_DIR"
    mkdir -p "$OUT_DIR"

    # Удаляем только live JSON, backfill-папку не трогаем.
    find "$LIVE_DIR" -maxdepth 1 -type f -name "*.json" -delete

    cd "$RUNTIME_DIR"

    MOCK_DATE="$DAY" NGINX_DIR="$LIVE_DIR" python3 generate_realistic_mock_json.py
    MOCK_DATE="$DAY" python3 link_mock_json_entities.py
    MOCK_DATE="$DAY" python3 fix_mock_entity_links_from_catalog.py

    JSON_COUNT="$(find "$LIVE_DIR" -maxdepth 1 -type f -name "*.json" | wc -l)"
    echo "live json files: ${JSON_COUNT}"

    if [ "$JSON_COUNT" -lt 20 ]; then
        echo "ERROR: too few json files for ${DAY}: ${JSON_COUNT}" >&2
        exit 1
    fi

    cp "$LIVE_DIR"/*.json "$OUT_DIR"/

    OUT_COUNT="$(find "$OUT_DIR" -maxdepth 1 -type f -name "*.json" | wc -l)"
    echo "backfill json files: ${OUT_COUNT}"

    if [ "$OUT_COUNT" -lt 20 ]; then
        echo "ERROR: too few copied json files for ${DAY}: ${OUT_COUNT}" >&2
        exit 1
    fi
done

echo
echo "WB mock backfill finished"

echo
echo "days generated:"
find "$BACKFILL_ROOT" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort | tail -80

echo
echo "total days:"
find "$BACKFILL_ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l

echo
echo "total json:"
find "$BACKFILL_ROOT" -mindepth 2 -maxdepth 2 -type f -name "*.json" | wc -l
