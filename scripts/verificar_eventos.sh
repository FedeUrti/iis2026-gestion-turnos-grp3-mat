#!/bin/bash

set -euo pipefail

echo "============================================="
echo "1. Monitoreando mensajes MQTT (30 segundos)"
echo "============================================="
echo "Escuchando eventos, Presiona Ctrl+C para finalizar escucha y ver la BD."
echo "---------------------------------------------"

# Escucha durante 30 segundos los eventos transmitidos por el broker Mosquitto
timeout 30s docker compose exec -T mosquitto mosquitto_sub -h localhost -t "turnos/#" -v || true

echo ""
echo "============================================="
echo "2. Consultando las ultimas reservas guardadas en BD"
echo "============================================="

# Consulta los registros directamente en el contenedor PostgreSQL
docker exec -it uruturn_db psql -U uruturn_user -d uruturn_db -c "SELECT * FROM reserva ORDER BY id_reserva DESC;"

echo "---------------------------------------------"
echo "Verificacion finalizada."


