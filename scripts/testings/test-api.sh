#!/bin/bash

BASE_URL="http://localhost:8000"

echo "====================================================="
echo " INICIANDO SCRIPT DE TESTING (API REST - URUTURN) "
echo "====================================================="

# ==========================================
# 1. PRUEBAS DE ESTABLECIMIENTOS
# ==========================================
echo -e "\n[ESTABLECIMIENTOS] -> POST: Creando nueva sucursal..."
curl -s -X POST $BASE_URL/establecimientos \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_comercial": "Clinica Testing",
    "direccion": "Calle Falsa 123",
    "telefono": "099111222",
    "correo_electronico": "test@clinica.uy",
    "horario_apertura": "08:00:00",
    "horario_cierre": "20:00:00"
  }'
echo -e "\n"

echo "[ESTABLECIMIENTOS] -> GET: Listando todos..."
curl -s -X GET $BASE_URL/establecimientos
echo -e "\n"

echo "[ESTABLECIMIENTOS] -> PUT: Actualizando establecimiento con ID 1..."
curl -s -X PUT $BASE_URL/establecimientos/1 \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_comercial": "Centro Salud Uru (Actualizado)",
    "direccion": "Av. 18 de Julio 1234",
    "telefono": "29000000",
    "correo_electronico": "admin@centrosalud.uy",
    "horario_apertura": "09:00:00",
    "horario_cierre": "18:00:00"
  }'
echo -e "\n"


# ==========================================
# 2. PRUEBAS DE PERSONAL
# ==========================================
echo -e "\n[PERSONAL] -> POST: Creando nuevo profesional..."
curl -s -X POST $BASE_URL/personal \
  -H "Content-Type: application/json" \
  -d '{
    "id_establecimiento": 1,
    "nombre": "Laura",
    "apellido": "Gomez",
    "email": "laura@centrosalud.uy",
    "telefono": "099000111",
    "cargo": "Pediatra",
    "especialidad": "Pediatría",
    "costo_consulta": 2000.00,
    "activo": true
  }'
echo -e "\n"

echo "[PERSONAL] -> GET: Obteniendo profesional con ID 1 (Ana Pereira)..."
curl -s -X GET $BASE_URL/personal/1
echo -e "\n"

echo "[PERSONAL] -> DELETE: Intentando eliminar profesional con ID 1 (Error esperado 1451/409)..."
# Esto lanzará el error de Foreign Key o pasará si no tiene reservas, probando el manejo de errores.
curl -s -X DELETE $BASE_URL/personal/1
echo -e "\n"


# ==========================================
# 3. PRUEBAS DE RESERVAS
# ==========================================
echo -e "\n[RESERVAS] -> POST: Solicitando turno exitoso..."
curl -s -X POST $BASE_URL/reservas \
  -H "Content-Type: application/json" \
  -d '{
    "email_solicitante": "paciente@gmail.com",
    "telefono_solicitante": "099444333",
    "id_personal": 1,
    "fecha_turno": "2026-12-05",
    "hora_turno": "10:00:00"
  }'
echo -e "\n"

echo "[RESERVAS] -> POST: Forzando error (409 Conflict) por turno duplicado..."
curl -s -X POST $BASE_URL/reservas \
  -H "Content-Type: application/json" \
  -d '{
    "email_solicitante": "otro.paciente@gmail.com",
    "telefono_solicitante": "099888999",
    "id_personal": 1,
    "fecha_turno": "2026-12-05",
    "hora_turno": "10:00:00"
  }'
echo -e "\n"

echo "[RESERVAS] -> GET: Listando reservas (esperando que el consumidor MQTT haya guardado)..."
sleep 2 # Damos 2 segundos para que Mosquitto procese el mensaje
curl -s -X GET $BASE_URL/reservas
echo -e "\n"

echo "====================================================="
echo " PRUEBAS FINALIZADAS "
echo "====================================================="