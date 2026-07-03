#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/wb_mock_api"
RUNTIME_DIR="$PROJECT_DIR/runtime"
WEB_DIR="/var/www/html"
LOG_DIR="/var/log/wb_mock_api"
LOG_FILE="$LOG_DIR/daily_generation.log"

mkdir -p "$RUNTIME_DIR" "$WEB_DIR" "$LOG_DIR"

{
  echo "============================================================"
  echo "WB mock daily generation started at $(date -Is)"
  echo "PROJECT_DIR=$PROJECT_DIR"
  echo "RUNTIME_DIR=$RUNTIME_DIR"
  echo "WEB_DIR=$WEB_DIR"

  cd "$PROJECT_DIR"

  echo
  echo "=== prepare runtime dir ==="
  rm -rf "$RUNTIME_DIR"/*
  cp specs/*.yaml "$RUNTIME_DIR"/
  cp scripts/*.py "$RUNTIME_DIR"/

  cd "$RUNTIME_DIR"

  echo
  echo "=== generate realistic mock json ==="
  NGINX_DIR="$WEB_DIR" python3 generate_realistic_mock_json.py

  echo
  echo "=== link mock json entities ==="
  python3 link_mock_json_entities.py

  echo
  echo "=== fix mock entity links from catalog ==="
  python3 fix_mock_entity_links_from_catalog.py

  echo
  echo "=== published json files ==="
  find "$WEB_DIR" -maxdepth 1 -name "*.json" -printf "%f\n" | sort
  echo "json_count=$(find "$WEB_DIR" -maxdepth 1 -name "*.json" | wc -l)"

  echo
  echo "WB mock daily generation finished at $(date -Is)"
} >> "$LOG_FILE" 2>&1
