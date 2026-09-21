#!/bin/bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FECHA="${FECHA:-2026-10-01}"

printf '1. Estado de la API\n'
curl --fail "$BASE_URL/health"
printf '\n\n2. Solicitar una reserva (se publica en MQTT)\n'
curl --fail --request POST "$BASE_URL/reservas" \
  --header "Content-Type: application/json" \
  --data "{\"email_solicitante\":\"paciente@correo.com\",\"telefono_solicitante\":\"099123456\",\"id_personal\":1,\"fecha_turno\":\"$FECHA\",\"hora_turno\":\"10:00:00\"}"
printf '\n\n3. Esperar al consumidor y consultar reservas\n'
sleep 2
curl --fail "$BASE_URL/reservas?fecha_turno=$FECHA"
printf '\n\n4. Ver la persistencia directamente en MySQL\n'
docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db \
  -e "SELECT * FROM reserva WHERE fecha_turno = '$FECHA';"
