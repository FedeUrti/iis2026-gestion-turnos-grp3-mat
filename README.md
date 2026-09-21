# Uru Turn! - Plataforma de Gestión de Turnos


Proyecto de gestión distribuida de turnos utilizando arquitectura orientada a eventos con MQTT y Docker.

## Requisitos
- Docker y Docker Compose

## Ejecución del Entorno
1. Iniciar el broker MQTT (Eclipse Mosquitto):
   docker compose up -d

## Ejecución de Scripts
- Escuchar solicitudes de turnos:
  ./scripts/suscribirse-turnos.sh

- Publicar un nuevo turno:
  ./scripts/publicar-turno.sh

## API de Reservas

La API REST se ejecuta en `http://localhost:8000`. Su documentación interactiva queda disponible en:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

Para levantar todo el entorno, incluyendo la API:

```bash
docker compose up -d --build
```

En una base creada con la version anterior, aplicar una sola vez la migracion del ID:

```bash
# Bash / Git Bash
docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db < db/migrate-reserva-id.sql
```

En PowerShell usar:

```powershell
Get-Content -Raw db\migrate-reserva-id.sql | docker compose exec -T db mysql -uuruturn_user -puruturn_password -Duruturn_db
```

El endpoint `POST /reservas` genera un ID aleatorio, lo publica como `turno.id` en MQTT y devuelve ese mismo ID. El consumidor valida el profesional, el horario y la disponibilidad antes de guardarlo explícitamente en `reserva.id_reserva`. Los endpoints `GET`, `PUT` y `DELETE` trabajan sobre la tabla `reserva`.

El contrato solicitado está en [parte3-api.yaml](parte3-api.yaml). Para ejecutar el ejemplo completo de alta y consulta:

```bash
bash scripts/test-reservas.sh
```

La explicación detallada del diseño y del código está en [docs/API_RESERVAS_EXPLICADA.md](docs/API_RESERVAS_EXPLICADA.md).

También se incluye una colección de Postman en [postman/UruTurn-Reservas.postman_collection.json](postman/UruTurn-Reservas.postman_collection.json). Se importa desde `File > Import` y se ejecutan las solicitudes en orden. La solicitud de alta guarda automáticamente el `reservaId` generado para usarlo en las operaciones siguientes.

## Autores
- Benjamín Gordillo
- Federico Urtiberea
- Santiago Lemos
- Ignacio Porcal


