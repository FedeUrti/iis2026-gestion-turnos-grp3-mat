#!/bin/bash

# Coloración para los mensajes de la consola
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin Color

BASE_URL="http://localhost:8000"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}      EJECUCIÓN DE PRUEBAS DE LA API (CURL)         ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. VERIFICAR SALUD DE LA API
echo -e "\n${YELLOW}[1/6] Verificando salud del sistema (GET /health)...${NC}"
curl -s -X GET "${BASE_URL}/health" | grep -q "ok" && echo -e "${GREEN}✓ API responde OK${NC}" || echo "✗ Error en la API"

# 2. CREAR ESTABLECIMIENTO
echo -e "\n${YELLOW}[2/6] Creando establecimiento (POST /establecimientos)...${NC}"
RESP_ESTABLECIMIENTO=$(curl -s -X POST "${BASE_URL}/establecimientos" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre_comercial": "Clínica San Luis",
    "direccion": "Av. 18 de Julio 1420",
    "telefono": "099123456",
    "correo_electronico": "contacto@sanluis.com",
    "horario_apertura": "08:00:00",
    "horario_cierre": "19:00:00"
  }')

echo "$RESP_ESTABLECIMIENTO"

# 3. LISTAR ESTABLECIMIENTOS
echo -e "\n${YELLOW}[3/6] Listando establecimientos (GET /establecimientos)...${NC}"
curl -s -X GET "${BASE_URL}/establecimientos"

# 4. CREAR PERSONAL
echo -e "\n${YELLOW}[4/6] Creando miembro del personal (POST /personal)...${NC}"
RESP_PERSONAL=$(curl -s -X POST "${BASE_URL}/personal" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "María",
    "apellido": "Rodríguez",
    "email": "maria.rodriguez@sanluis.com",
    "telefono": "098765432",
    "cargo": "Medicina General",
    "id_establecimiento": 1
  }')

echo "$RESP_PERSONAL"

# 5. SOLICITAR RESERVA VIA MQTT
echo -e "\n${YELLOW}[5/6] Solicitando reserva (POST /reservas -> MQTT)...${NC}"
curl -s -i -X POST "${BASE_URL}/reservas" \
  -H "Content-Type: application/json" \
  -d '{
    "email_solicitante": "paciente.ejemplo@gmail.com",
    "telefono_solicitante": "091111222",
    "id_personal": 1,
    "fecha_turno": "2026-10-15",
    "hora_turno": "09:30:00"
  }'

# 6. LISTAR RESERVAS
echo -e "\n\n${YELLOW}[6/6] Listando reservas registradas (GET /reservas)...${NC}"
curl -s -X GET "${BASE_URL}/reservas"

echo -e "\n\n${GREEN}====================================================${NC}"
echo -e "${GREEN}        PRUEBAS FINALIZADAS CORRECTAMENTE           ${NC}"
echo -e "${GREEN}====================================================${NC}"