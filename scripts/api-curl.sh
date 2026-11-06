#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

usage() {
  cat <<'EOF'
Uso:
  bash scripts/api-curl.sh METODO RUTA [JSON]

METODO: GET, POST, PUT o DELETE
RUTA:   ruta de la API, empezando con /
JSON:   cuerpo opcional para POST y PUT, entre comillas simples

Ejemplos:
  bash scripts/api-curl.sh GET /health
  bash scripts/api-curl.sh GET /establecimientos
  bash scripts/api-curl.sh GET '/personal?id_establecimiento=1'
  bash scripts/api-curl.sh POST /establecimientos \
    '{"nombre_comercial":"Centro Nuevo","direccion":"Av. Central 123","telefono":"099123456","correo_electronico":"centro@example.com","horario_apertura":"08:00:00","horario_cierre":"18:00:00"}'
  bash scripts/api-curl.sh POST /personal \
    '{"nombre":"Ana","apellido":"Pérez","email":"ana@example.com","telefono":"099123456","cargo":"Médica","id_establecimiento":1}'
  bash scripts/api-curl.sh POST /reservas \
    '{"nombre":"Cliente","email_solicitante":"cliente@example.com","telefono_solicitante":"099123456","id_establecimiento":1,"id_personal":1,"fecha_turno":"2027-01-15","hora_turno":"10:00:00"}'
  bash scripts/api-curl.sh GET '/facturas?email_cliente=cliente@example.com'

Configurar otro host:
  BASE_URL=http://servidor:8000 bash scripts/api-curl.sh GET /health
EOF
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

method="$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"
path="$2"
body="${3:-}"

case "$method" in
  GET|POST|PUT|DELETE) ;;
  *)
    printf 'Método no permitido: %s\n' "$method" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$path" != /* ]]; then
  printf 'La ruta debe comenzar con /: %s\n' "$path" >&2
  exit 2
fi

if [[ ( "$method" == POST || "$method" == PUT ) && -z "$body" ]]; then
  printf '%s requiere un cuerpo JSON.\n' "$method" >&2
  usage >&2
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  printf 'No se encontró curl. Instala Git for Windows/WSL con curl disponible.\n' >&2
  exit 1
fi

url="${BASE_URL%/}${path}"
printf '%s %s\n' "$method" "$url"

if [[ "$method" == POST || "$method" == PUT ]]; then
  response="$(curl --silent --show-error \
    --request "$method" \
    --header "Content-Type: application/json" \
    --data "$body" \
    --write-out $'\n%{http_code}' \
    -- "$url")"
else
  response="$(curl --silent --show-error \
    --request "$method" \
    --write-out $'\n%{http_code}' \
    -- "$url")"
fi

http_status="${response##*$'\n'}"
response_body="${response%$'\n'*}"

printf '\nEstado HTTP: %s\n' "$http_status"
printf 'Respuesta:\n'

if [[ -z "$response_body" ]]; then
  printf '(sin contenido)\n'
elif command -v jq >/dev/null 2>&1; then
  if ! printf '%s' "$response_body" | jq --color-output .; then
    printf '%s\n' "$response_body"
  fi
elif command -v python >/dev/null 2>&1; then
  if ! printf '%s' "$response_body" | python -m json.tool; then
    printf '%s\n' "$response_body"
  fi
elif command -v python3 >/dev/null 2>&1; then
  if ! printf '%s' "$response_body" | python3 -m json.tool; then
    printf '%s\n' "$response_body"
  fi
else
  printf '%s\n' "$response_body"
fi
