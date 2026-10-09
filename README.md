# UruTurn!

Aplicación de gestión de turnos con FastAPI, MySQL, MQTT y Docker.

## Iniciar

```bash
docker compose up -d --build
```

La API está disponible en `http://localhost:8000/docs`. phpMyAdmin está en
`http://localhost:8080`.

## Funcionalidades

- Administración de establecimientos, profesionales y reservas.
- Validación de reservas en segundo plano y detección de horarios ocupados.
- Registro de clientes al crear una reserva.
- Facturación mensual por cliente para los turnos atendidos.
- Integración MQTT para publicar y recibir solicitudes de turnos.

## Pruebas

Con la API y MySQL levantados:

```bash
bash scripts/test-reservas.sh
bash scripts/test-facturas.sh
```

Las pruebas crean datos temporales y los eliminan al finalizar. Requieren Bash,
`curl` y Docker Compose. `test-reservas.sh` ejecuta el worker sobre todas las
reservas pendientes, no solo las de prueba.

## Documentación de la API

El contrato está en [parte3-api.yaml](parte3-api.yaml).
