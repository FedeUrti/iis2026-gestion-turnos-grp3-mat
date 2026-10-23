#!/usr/bin/env bash
set -euo pipefail

TOPIC="turnos/solicitudes"

echo "Escuchando mensajes en $TOPIC. Presione Ctrl+C para detener."
docker compose exec mosquitto mosquitto_sub \
  -h localhost \
  -p 1883 \
  -t "$TOPIC" \
  -v