#!/usr/bin/env bash
set -euo pipefail

TOPIC="turnos/solicitudes"
PAYLOAD='{
  "status": "turno_creado",
  "fechaHora": "2026-09-01T10:15:00",
  "turno": {
    "id": 35,
    "email_cliente": "a@a.com",
    "telefono_cliente": 11111111,
    "idPersonal": 8,
    "fecha": "2026-09-15",
    "hora": "14:30"
  }
}'

docker compose exec -T mosquitto mosquitto_pub \
  -h localhost \
  -p 1883 \
  -t "$TOPIC" \
  -m "$PAYLOAD"

echo "Turno publicado en $TOPIC."