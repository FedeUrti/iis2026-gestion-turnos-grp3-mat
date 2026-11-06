#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
API_SCRIPT="$PROJECT_DIR/scripts/api-curl.sh"

echo "Comprobación de lectura de la API (no crea, modifica ni elimina datos)."
for path in \
  /health \
  /establecimientos \
  /personal \
  /reservas \
  /facturas
do
  printf '\n--- GET %s ---\n' "$path"
  bash "$API_SCRIPT" GET "$path"
done