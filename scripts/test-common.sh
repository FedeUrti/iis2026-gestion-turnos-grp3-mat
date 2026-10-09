#!/bin/bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
DB_USER="${DB_USER:-uruturn_user}"
DB_PASSWORD="${DB_PASSWORD:-uruturn_password}"
DB_NAME="${DB_NAME:-uruturn_db}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_test_environment() {
  command -v curl >/dev/null || fail "Se necesita curl."
  command -v docker >/dev/null || fail "Se necesita Docker."
  docker compose exec -T db mysql \
    "-u$DB_USER" "-p$DB_PASSWORD" "$DB_NAME" -N -e "SELECT 1" \
    >/dev/null 2>&1 || fail "MySQL no está disponible. Levanta db y reservas-api."
  curl --silent --show-error --fail "$BASE_URL/health" >/dev/null \
    || fail "La API no está disponible en $BASE_URL."
}

datetime_minutes_ago() {
  docker compose exec -T reservas-api python -c \
    "from datetime import datetime, timedelta, timezone; now = datetime.now(timezone(timedelta(hours=-3))) - timedelta(minutes=int('$1')); print(now.strftime('%Y-%m-%d %H:%M:00'))"
}

datetime_minutes_from_now() {
  docker compose exec -T reservas-api python -c \
    "from datetime import datetime, timedelta, timezone; now = datetime.now(timezone(timedelta(hours=-3))).replace(second=0, microsecond=0); print((now + timedelta(minutes=int('$1') + 1)).strftime('%Y-%m-%d %H:%M:00'))"
}

date_next_month() {
  docker compose exec -T reservas-api python -c \
    "from datetime import date, timedelta; today = date.today(); first = today.replace(day=1); month = first.month % 12 + 1; year = first.year + (first.month == 12); print((first.replace(year=year, month=month) + timedelta(days=int('$1'))).isoformat())"
}

db_scalar() {
  docker compose exec -T db mysql \
    "-u$DB_USER" "-p$DB_PASSWORD" "$DB_NAME" -N -B -e "$1" 2>/dev/null \
    | tr -d '\r'
}

api_request() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local response

  if [[ -n "$body" ]]; then
    response="$(curl --silent --show-error --request "$method" "$url" \
      --header "Content-Type: application/json" \
      --data "$body" --write-out $'\n%{http_code}')"
  else
    response="$(curl --silent --show-error --request "$method" "$url" \
      --write-out $'\n%{http_code}')"
  fi

  API_STATUS="${response##*$'\n'}"
  API_BODY="${response%$'\n'*}"
}

json_value() {
  local json="$1"
  local path="$2"
  printf '%s' "$json" | docker compose exec -T reservas-api python -c '
import json
import sys

value = json.load(sys.stdin)
for key in sys.argv[1].split("."):
    if key == "length":
        value = len(value)
    else:
        value = value[int(key)] if isinstance(value, list) else value[key]
print(value)
' "$path"
}

create_reservation() {
  local email="$1"
  local name="$2"
  local date="$3"
  local time="$4"
  local establishment_id="${5:-1}"
  local personal_id="${6:-1}"
  local body

  body="$(printf \
    '{"nombre":"%s","email_solicitante":"%s","telefono_solicitante":"099123456","id_establecimiento":%s,"id_personal":%s,"fecha_turno":"%s","hora_turno":"%s"}' \
    "$name" "$email" "$establishment_id" "$personal_id" "$date" "$time")"
  api_request POST "$BASE_URL/reservas" "$body"
}

process_reservation_worker() {
  docker compose exec -T reservas-api python -c \
    "from worker_reservas import procesar_reservas_pendientes; print(procesar_reservas_pendientes())" \
    >/dev/null
}

process_invoice_worker() {
  docker compose exec -T reservas-api python -c \
    "from worker_facturas import facturar_turnos_atendidos; print(facturar_turnos_atendidos())"
}
