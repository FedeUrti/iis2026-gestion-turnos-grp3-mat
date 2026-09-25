# UruTurn! - Plataforma de gestión de turnos

Proyecto de gestión distribuida de turnos con arquitectura orientada a eventos, construido con FastAPI, MySQL, MQTT y Docker. El sistema permite registrar establecimientos, profesionales y reservas, y coordina la creación y validación de turnos mediante mensajes en un broker MQTT.

## ¿Qué incluye el proyecto?

- API REST en FastAPI para administrar:
  - `/establecimientos`
  - `/personal`
  - `/reservas`
- Base de datos MySQL con esquema inicial en [db/init.sql](db/init.sql)
- Broker MQTT con Eclipse Mosquitto para la cola de mensajes de turnos
- Servicios auxiliares en Python para publicar y consumir eventos
- Panel de administración de MySQL con phpMyAdmin

## Arquitectura

El entorno levantado por Docker Compose incluye estos componentes principales:

- `mosquitto`: broker MQTT para el canal `turnos/solicitudes`
- `db`: base de datos MySQL con las tablas `establecimiento`, `personal` y `reserva`
- `phpmyadmin`: interfaz web para inspeccionar la base de datos en `http://localhost:8080`
- `generador`: publicador de mensajes de ejemplo para simular la creación de turnos
- `consumidor`: suscriptor que valida y persiste reservas en la base de datos
- `reservas-api`: API FastAPI principal de la aplicación

## Requisitos

- Docker
- Docker Compose

## Levantar el entorno

```bash
docker compose up -d --build
```

Esto inicia la infraestructura completa del proyecto, incluyendo broker, base de datos, API y servicios asociados.

## API REST

La API queda disponible en:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

### Endpoints principales

- `GET /establecimientos`, `POST /establecimientos`, `PUT /establecimientos/{id}`, `DELETE /establecimientos/{id}`
- `GET /personal`, `POST /personal`, `PUT /personal/{id}`, `DELETE /personal/{id}`
- `GET /reservas`, `POST /reservas`, `PUT /reservas/{id}`, `DELETE /reservas/{id}`

El contrato de la API está definido en [parte3-api.yaml](parte3-api.yaml).

## Flujo de reservas

El flujo real del proyecto es el siguiente:

1. La API valida si el profesional existe, está activo y si el horario solicitado ya está ocupado.
2. Si la validación local pasa, la API genera un ID de turno y publica un evento MQTT en el topic `turnos/solicitudes`.
3. El consumidor escucha ese topic y realiza la validación final del profesional y la disponibilidad antes de persistir la reserva en la tabla `reserva`.
4. Las consultas y modificaciones de reservas se hacen sobre la tabla `reserva` mediante los endpoints de la API.

En otras palabras, la API no solo expone los recursos REST; también forma parte del mecanismo distribuido con eventos MQTT que coordina la creación de turnos.

## Scripts de ejemplo

### Escuchar eventos MQTT

```bash
./scripts/suscribirse-turnos.sh
```

### Publicar un mensaje de prueba

```bash
./scripts/publicar-turno.sh
```

### Ejecutar la prueba completa de alta y consulta de reservas

```bash
bash scripts/test-reservas.sh
```

Este script hace una solicitud de ejemplo a `POST /reservas`, espera a que el consumidor procese el evento y consulta el resultado persistido.

## Migración de base existente

Si la base de datos ya fue creada con una versión anterior, puede ser necesario aplicar una migración puntual del ID de reserva:

```bash
# Bash / Git Bash
docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db < db/migrate-reserva-id.sql
```

En PowerShell:

```powershell
Get-Content -Raw db\migrate-reserva-id.sql | docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db
```

## Autores

- Benjamín Gordillo
- Federico Urtiberea
- Santiago Lemos
- Ignacio Porcal


