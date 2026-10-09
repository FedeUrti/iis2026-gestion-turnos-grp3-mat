#!/bin/bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FECHA="${FECHA:-$(date -d '+7 days' +%F)}"

printf '1. Estado de la API\n'
curl --fail "$BASE_URL/health"
printf '\n\n2. Solicitar una reserva por la API\n'
RESPUESTA=$(curl --fail --silent --show-error --request POST "$BASE_URL/reservas" \
  --header "Content-Type: application/json" \
  --data "{\"nombre\":\"Ana Pérez\",\"email_solicitante\":\"paciente@correo.com\",\"telefono_solicitante\":\"099123456\",\"id_establecimiento\":1,\"id_personal\":1,\"fecha_turno\":\"$FECHA\",\"hora_turno\":\"10:00:00\"}")
printf '%s\n' "$RESPUESTA"
ID_RESERVA=$(printf '%s' "$RESPUESTA" | sed -n 's/.*"id":\([0-9]*\).*/\1/p')

printf '\n\n3. Esperar el ciclo de FastAPI y consultar la reserva\n'
for intento in $(seq 1 65); do
  ESTADO=$(curl --fail --silent --show-error "$BASE_URL/reservas/$ID_RESERVA")
  if ! printf '%s' "$ESTADO" | grep -q '"estado_reserva":"PENDIENTE"'; then
    break
  fi
  sleep 1
done
printf '%s\n' "$ESTADO"

printf '\n\n4. Listar las reservas\n'
curl --fail "$BASE_URL/reservas"

printf '\n\n5. Ver la persistencia directamente en MySQL\n'
docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db \
  -e "SELECT id_reserva, email_solicitante, id_establecimiento, id_personal, fecha_turno, hora_turno, estado_reserva FROM reserva WHERE fecha_turno = '$FECHA' ORDER BY hora_turno;"
