#!/usr/bin/env bash
set -euo pipefail

TOPIC="turnos/solicitudes"
ID_TURNO="${ID_TURNO:-$(date +%s)}"
FECHA_TURNO="${FECHA_TURNO:-$(date -d '+1 day' +%F)}"
PAYLOAD='{
  "status": "turno_creado",
  "fechaHora": "'"$(date --iso-8601=seconds)"'",
  "turno": {
    "id": '"$ID_TURNO"',
    "email_cliente": "a@a.com",
    "nombre_cliente": "Ana",
    "telefono_cliente": 11111111,
    "idEstablecimiento": 1,
    "idPersonal": 1,
    "fecha": "'"$FECHA_TURNO"'",
    "hora": "14:30"
  }
}'

docker compose exec -T mosquitto mosquitto_pub \
  -h localhost \
  -p 1883 \
  -t "$TOPIC" \
  -m "$PAYLOAD"

echo "Turno publicado en $TOPIC."