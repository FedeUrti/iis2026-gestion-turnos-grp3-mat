#!/bin/bash

CONTAINER_NAME="uruturn_db"
DB_USER="uruturn_user"
DB_NAME="uruturn_db"
DB_PASSWORD="uruturn_password" # Misma contraseña que en docker-compose.yml

echo "=================================================="
echo "      Uru Turn! - CONSULTA DE BASE DE DATOS       "
echo "=================================================="
echo ""

if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: El contenedor $CONTAINER_NAME no está corriendo."
    echo "Ejecuta 'docker compose up -d' antes de lanzar este script."
    exit 1
fi

echo "---> 1. ESTABLECIMIENTOS REGISTRADOS:"
docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -D $DB_NAME -e \
  "SELECT id_establecimiento, nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre FROM establecimiento;"

echo ""
echo "---> 2. PERSONAL DEL ESTABLECIMIENTO:"
docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -D $DB_NAME -e \
  "SELECT id_personal, id_establecimiento, nombre, especialidad, costo_consulta, duracion_atencion, activo FROM personal;"

echo ""
echo "---> 3. CLIENTES REGISTRADOS:"
docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -D $DB_NAME -e \
  "SELECT email, nombre, telefono FROM cliente ORDER BY email;"

echo ""
echo "---> 4. RESERVAS (PENDIENTES, RECHAZADAS Y AGENDADAS):"
docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -D $DB_NAME -e \
  "SELECT id_reserva, fecha_reservado, email_solicitante, telefono_solicitante, id_establecimiento, id_personal, fecha_turno, hora_turno, estado_reserva FROM reserva ORDER BY id_reserva;"

echo ""
echo "---> 5. FACTURAS E ÍTEMS:"
docker exec -it $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -D $DB_NAME -e \
  "SELECT f.id_factura, c.nombre, f.email_cliente, f.periodo, f.total, i.id_reserva, i.nombre_profesional, i.descripcion, i.precio_unitario FROM factura f JOIN cliente c ON c.email = f.email_cliente LEFT JOIN factura_item i ON i.id_factura = f.id_factura ORDER BY f.periodo, f.email_cliente, i.id_item;"

echo ""
echo "=================================================="
echo "          FIN DE CONSULTA DE DATOS                "
echo "=================================================="