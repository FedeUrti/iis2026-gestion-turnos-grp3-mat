#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================="
echo "1. Monitoreando mensajes MQTT (30 segundos)"
echo "============================================="
echo "Escuchando eventos, Presiona Ctrl+C para finalizar escucha y ver la BD."
echo "---------------------------------------------"

SUBSCRIBER_PID=""

mostrar_reservas() {
	echo ""
	echo "============================================="
	echo "2. Consultando las ultimas reservas guardadas en BD"
	echo "============================================="
	docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db \
		-e "SELECT * FROM reserva ORDER BY id_reserva DESC;"
	echo "---------------------------------------------"
	echo "Verificacion finalizada."
}

detener_y_mostrar() {
	if [ -n "$SUBSCRIBER_PID" ]; then
		kill "$SUBSCRIBER_PID" 2>/dev/null || true
		wait "$SUBSCRIBER_PID" 2>/dev/null || true
	fi
	mostrar_reservas
	exit 0
}

trap detener_y_mostrar INT TERM

# Se ejecuta en segundo plano para que Ctrl+C sea manejado por este script.
docker compose exec -T mosquitto mosquitto_sub \
	-h localhost -t "turnos/solicitudes" -v &
SUBSCRIBER_PID=$!

for segundos in $(seq 30 -1 1); do
	printf "\rEscuchando... quedan %02d segundos. Presiona Ctrl+C para terminar. " "$segundos"
	sleep 1
done

detener_y_mostrar


